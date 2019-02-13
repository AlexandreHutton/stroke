import glob
import os
import numpy as np
import pandas as pd
import rampwf as rw
from nilearn.image import load_img
from sklearn.model_selection import StratifiedShuffleSplit

problem_title = 'Stroke segmentation'
_target_column_name = 'species'
_prediction_label_names = ['setosa', 'versicolor', 'virginica']
# A type (class) which will be used to create wrapper objects for y_pred
Predictions = rw.prediction_types.make_multiclass(
    label_names=_prediction_label_names)
# An object implementing the workflow
workflow = rw.workflows.Classifier()

score_types = [
    rw.score_types.Accuracy(name='acc'),
    rw.score_types.ClassificationError(name='error'),
    rw.score_types.NegativeLogLikelihood(name='nll'),
    rw.score_types.F1Above(name='f1_70', threshold=0.7),
]


def get_cv(X, y):
    cv = StratifiedShuffleSplit(n_splits=2, test_size=0.2, random_state=57)
    return cv.split(X, y)


def _read_ids(path, split='train'):
    # FIXME: This should be replaced by hardcoding the IDs in train and test
    # CSV files.
    path_metadata = os.path.join(
        path, 'data', 'images', 'ATLAS_Meta-Data_Release_1.1_standard_mni.csv'
    )
    df = pd.read_csv(path_metadata)
    # FIXME: remove the duplicate for the moment
    ids = df['INDI Subject ID'].unique()
    rng = np.random.RandomState(42)
    train_id = rng.choice(ids, size=int(ids.size * 0.8), replace=False)
    test_id = np.setdiff1d(ids, train_id, assume_unique=True)

    # FIXME: return only 20 first IDs 
    if split == 'train':
        return train_id[:20]

    return test_id[:20]

def _get_patient_path(path, subject_id):
    path_metadata = os.path.join(
        path, 'data', 'images', 'ATLAS_Meta-Data_Release_1.1_standard_mni.csv'
    )
    df = pd.read_csv(path_metadata)
    # FIXME: just to take the first occurrence
    site_dir = df[df['INDI Subject ID'] == subject_id]['INDI Site ID'].iloc[0]
    subject_id = '{:06d}'.format(subject_id)
    path_patient = os.path.join(
        path, 'data', 'images', site_dir, subject_id, 't01'
    )
    return path_patient

def _read_brain_image(path, subject_id):
    path_metadata = os.path.join(
        path, 'data', 'images', 'ATLAS_Meta-Data_Release_1.1_standard_mni.csv'
    )
    df = pd.read_csv(path_metadata)
    # FIXME: just to take the first occurrence
    site_dir = df[df['INDI Subject ID'] == subject_id]['INDI Site ID'].iloc[0]
    subject_id = '{:06d}'.format(subject_id)
    
    path_patient = _get_patient_path(path, subject_id)
    path_brain_image = os.path.join(path_patient,
        subject_id + '_t1w_deface_stx.nii.gz'
    )
    return load_img(path_brain_image).get_data()

def _combine_masks(path_masks):
    mask = load_img(path_masks[0]).get_data()
    for next_mask_path in path_masks[1:]:
        np.add(mask, load_img(next_mask_path).get_data())

    mask[mask > 1] = 1
    return mask

def _read_stroke_segmentation(path, subject_id):
    path_patient = _get_patient_path(path, subject_id)
    path_masks = glob.glob(str(path_patient)+'/*_LesionSmooth_*.nii.gz')
    
    mask = _combine_masks(path_masks)  
    return mask  

def _read_data(path, split_ids):
    # the data will be of dimensions: #img,h,v,d
    X = np.stack([_read_brain_image(path, subject_id)
                   for subject_id in split_ids])

    Y = np.stack([_read_stroke_segmentation(path, subject_id)
                   for subject_id in split_ids])
    return X, Y


def get_train_data(path='.'):
    # generate the training IDs
    train_id = _read_ids(path, split='train')
    return _read_data(path, train_id)


def get_test_data(path='.'):
    # generate the testing IDs
    test_id = _read_ids(path, split='test')
    return _read_data(path, test_id)
