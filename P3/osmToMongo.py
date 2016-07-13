#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json
from pymongo import MongoClient


lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z_]*):([a-z_]*)$')

#added after v1, looks for lower case followed by single uppercase
#for example the kS in nickShaw matches
lowerUpper = re.compile(r'([a-z])([A-Z])')

phoneNumber = re.compile(r'^[+][0-9][-][0-9]{3}[-][0-9]{3}[-][0-9]{4}$')

postCode = re.compile(r'^[A-Z][0-9][A-Z][\s][0-9][A-Z][0-9]$')
postCodeStripped = re.compile(r'^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$')

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]

#converts a lowercase followed by a uppercase to all lowercase and sepperated
#by a _. For example nickShaw becomes nick_shaw
def _replaceLowerUpper(match):

    lower = str(match.group(1))
    upper = str(match.group(2))

    return lower + "_" + upper.lower()

def shape_element(element,log):
    node = {}
    if element.tag == "node" or element.tag == "way" :

        node['type'] = element.tag

        #First parse the attributes
        #created and pos take special care

        #For created make a subdict called 'created' for all atribiutes
        #with names found in the CREATED array.

        #For pos combine the lat and lon fields into a 2 element array with
        #floats

        #Everything else just add to the dict with the name being the key and
        #value being the value

        attrib = element.attrib
        created = {}
        pos = [0.0,0.0]

        for k in attrib:

            if k in CREATED:
                created[k] = attrib[k]
            elif k == 'lat':
                pos[0] = float(attrib[k])
            elif k == 'lon':
                pos[1] = float(attrib[k])
            else:
                node[k] = attrib[k]

        node['pos'] = pos
        node['created'] = created

        #now parse the tags
        #All tags should have a k and v field.

        #For tags with keys without a : in them, add them to the dict with the
        #k being the key and v the value.

        #If the key has a single : make a subdict
        for tag in element.iter('tag'):
            k = tag.attrib['k']
            v = tag.attrib['v']

            # preProcessLog version 1 - fix upper case letters.

            #first if there are any lower case letters followed by a upper case
            #add a _ between the lower and upper case and make the upper case
            #lower
            k = re.sub(lowerUpper,_replaceLowerUpper,k)

            #now make everyting lowercase
            k = k.lower()

            # preProcessLog version 2 - replace all - with _
            k = str.replace(k,"-","_")

            #first check if k is okay
            lowerMatch = lower.search(k)
            lowerColonMatch = lower_colon.search(k)

            if lowerMatch:
                node[k] = v

            #if there is a single colon, make a 'subDict' with the
            #value before the column as the key in the main dict, and
            #value after the colon the key in the subdict
            elif lowerColonMatch:
                subDict = lowerColonMatch.groups()[0]
                subDictKey = lowerColonMatch.groups()[1]

                #Rename the address sub dict
                if subDict == 'addr':
                    subDict = "address"

                #To avoid conflicts with other keys, add _attribs to the
                #subdict key
                else:
                    subDict = subDict + "_attribs"

                if not subDict in node:
                    node[subDict] = {}

                node[subDict][subDictKey] = v

            #Bad key. Record in log, but do not add to dataset
            else:
                log.write('Bad tag key, not added: %s\n' % (k))


        #parse the node references
        node_refs = []
        for nd in element.iter('nd'):
            node_refs.append(nd.attrib['ref'])

        if (len(node_refs) > 0):
            node['node_refs'] = node_refs

        return cleanDocument(node)
    else:
        return None

'''
uniqueCount counts how many orcunces of a certain name is
'''
def uniqueCount(nameIndex,name):

    if name in nameIndex:
        nameIndex[name] += 1

    else:
        nameIndex[name] = 1

    return nameIndex

def process_map(file_in, preProcessLog = 'pre_process_log.txt', pretty = False):
    file_out = "{0}.json".format(file_in)

    #Get rid of the .osm
    file_out = str.replace(file_out,".osm","")

    data = []
    amenites = dict()

    with codecs.open(file_out, "w") as fo:
        with open(preProcessLog, 'w') as log:
            for _, element in ET.iterparse(file_in):
                el = shape_element(element,log)
                if el:
                    data.append(el)

                    if 'amenity' in el:
                        amenites = uniqueCount(amenites,el['amenity'])
                    if pretty:
                        fo.write(json.dumps(el, indent=2)+"\n")
                    else:
                        fo.write(json.dumps(el) + "\n")

    print '%d elelments processed and converted to json.\n' \
          'New file created:\t\t%s\nLog file for preproccessing:\t%s' \
          % (len(data),file_out,preProcessLog)
    return data

'''
cleanDocument cleans a doucment according to different rules
'''
def cleanDocument(d):

    #Clean cafe
    if('amenity' in d and d['amenity'] == 'cafe'):
        d['cuisine'] = 'coffee_shop'

    #Clean the format of the phone number if there is a phone number
    #and the phone number is not already in the correct format
    if('phone' in d and not phoneNumber.match(d['phone'])):

        #The phone number with nothing but digits
        stripped = re.sub('[^0-9]', '', d['phone'])

        #The number should be of length 10 or 11
        #If it is 10, add a 1 to the start
        if(len(stripped) == 10):
            stripped = '1' + stripped

        #Put into the correct format +#-###-###-####
        if(len(stripped) == 11):
            d['phone'] = '+' + stripped[0] \
                         + '-' + stripped[1:4] \
                         + '-' + stripped[4:7] \
                         + '-' + stripped[7:11]

    #Used to audit the phone number format
    if('phone' in d):
        d['phone_format'] = re.sub('[0-9]', '#', d['phone'])

    #Clean the format of the postcode if there is a postcode
    #and the postCode is not allready in the right format
    if ('address' in d \
        and 'postcode' in d['address'] \
        and not postCode.match(d['address']['postcode'])):

        #Remove everything but letter and numbers. Make it upper case
        stripped = re.sub('[^0-9A-Za-z]', '', d['address']['postcode']).upper()

        #Check if the stripped (only letters and numbers) post code is valid
        #Drop it if it isn't
        if(postCodeStripped.match(stripped)):
            d['address']['postcode'] = stripped[0:3] + " " + stripped[3:]
        else:
            d['address'].pop("postcode", None)

    #Used to audit postal code format
    #digits to #, lower case to L, upper case to U
    if ('address' in d and 'postcode' in d['address']):
        d['address']['post_format'] = re.sub('[0-9]', '#', d['address']['postcode'])
        d['address']['post_format'] = re.sub('[a-z]', 'L', d['address']['post_format'])
        d['address']['post_format'] = re.sub('[A-Z]', 'U', d['address']['post_format'])

    return d

def loadIntoMongoDB(data):
    client = MongoClient()
    client = MongoClient('localhost', 27017)

    db = client.p3

    db.maps.delete_many({})
    db.maps.insert(data)

    print "maps document set in mongodb re-loaded"
