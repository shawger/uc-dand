#!/usr/bin/python

import sys
import pickle
sys.path.append("../tools/")

#For transforming data
import numpy as np
import pandas as pd

from feature_format import featureFormat, targetFeatureSplit
from tester import dump_classifier_and_data

### Task 1: Select what features you'll use.
### features_list is a list of strings, each of which is a feature name.
### The first feature must be "poi".

#See section 'Feature Selection' in notebook for justification
features_list =  ['poi',
                  'to_messages',
                  'from_messages',
                  'from_poi_to_this_person',
                  'from_this_person_to_poi',
                  'shared_receipt_with_poi']


### Load the dictionary containing the dataset
with open("final_project_dataset.pkl", "r") as data_file:
    data_dict = pickle.load(data_file)

### Task 2: Remove outliers
### Task 3: Create new feature(s)
#For adding data, removing data and transforming data,
#I am using pandas
df = pd.DataFrame.from_dict(data_dict,orient='index')

#Set data in the features to numeric values
#Exclude first record because it is poi
for feature in features_list[1:]:
    df[feature] = pd.to_numeric(df[feature],errors='coerce')

#Drop the total field and THE TRAVEL AGENCY IN THE PARK
df = df.drop('TOTAL')
df = df.drop('THE TRAVEL AGENCY IN THE PARK')

#Add new feature: finance_field_count
finance_fields = ['salary',
                 'bonus',
                 'restricted_stock',
                 'expenses',
                 'other',
                 'deferred_income',
                 'long_term_incentive']

#Put 0 in for all the NaN records. See 'Missing Data' in the notebook
#For some reason doing the following didn't work, so I used a loop:
# df[features_list[1:]] = df[features_list[1:]].fillna(0)
for feature in features_list[1:]:
    df[feature] = df[feature].fillna(0)

#For every field that does not have a null value, increment the counter
df['finance_field_count'] = df[finance_fields].notnull().sum(axis=1)
features_list.append('finance_field_count')

#The to rate is the number of emails from a poi to this person / the number
#of emails received. If they received to emails, then
#the to_rate is 0
df.ix[df.to_messages==0, 'to_rate'] = 0
df.ix[df.to_messages!=0, 'to_rate'] = \
    df[df.to_messages!=0]['from_poi_to_this_person'] \
    / df[df.to_messages!=0]['to_messages']

#The from rate is the number of emails to a poi / the number
#of emails sent. If they received to emails, then
#the to_rate is 0
df.ix[df.from_messages==0, 'from_rate'] = 0
df.ix[df.from_messages!=0, 'from_rate'] = \
    df[df.from_messages!=0]['from_this_person_to_poi'] \
    / df[df.from_messages!=0]['from_messages']

#Remake the features_list to use added variables
features_list =  ['poi',
                  'to_rate',
                  'from_rate',
                  'shared_receipt_with_poi',
                  'finance_field_count']

#Scale the features using sklearn
from sklearn import preprocessing
df[features_list[1:]] = preprocessing.scale(df[features_list[1:]])

### Store to my_dataset for easy export below.
my_dataset =  df.to_dict(orient='index')

### Extract features and labels from dataset for local testing (not required)
'''data = featureFormat(my_dataset, features_list, sort_keys = True)
labels, features = targetFeatureSplit(data)'''

# See 'Classifier' section in notebook for more information
from sklearn import tree
from sklearn.ensemble import RandomForestClassifier
clf = RandomForestClassifier(n_estimators=50,max_depth=2,min_samples_split=7,class_weight='balanced',max_features='auto')


#Dump the data
dump_classifier_and_data(clf, my_dataset, features_list)