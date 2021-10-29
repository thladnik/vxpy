import cv2
import h5py

sample_files = {'Multi_Fish_Eyes_Cam@20fps': 'Fish_eyes_multiple_fish_30s.avi',
               'Single_Fish_Eyes_Cam@20fps': 'Fish_eyes_spontaneous_saccades_40s.avi',
               'Single_Fish_Spontaneous_1@115fps': 'single_zebrafish_eyes.avi',
               'Single_Fish_Spontaneous_2@115fps': 'single_zebrafish_eyes0001.avi',
                'Single_Fish_Spontaneous_3@115fps': 'single_zebrafish_eyes0002.avi',
                'Single_Fish_Spontaneous_4@115fps': 'single_zebrafish_eyes0003.avi',
               'Single_Fish_Spontaneous_1@30fps': 'OKR_2020-12-08_multi_phases.avi'}

fps = {'Multi_Fish_Eyes_Cam@20fps': 20,
        'Single_Fish_Eyes_Cam@20fps': 20,
        'Single_Fish_Spontaneous_1@115fps': 115,
        'Single_Fish_Spontaneous_2@115fps': 115,
        'Single_Fish_Spontaneous_3@115fps': 115,
        'Single_Fish_Spontaneous_4@115fps': 115,
        'Single_Fish_Spontaneous_1@30fps': 30}

formats = {'Multi_Fish_Eyes_Cam@20fps': ['RGB8 (752x480)', 'Y800 (752x480)', 'RGB8 (640x480)', 'Y800 (640x480)', 'RGB8 (480x480)', 'Y800 (480x480)'],
            'Single_Fish_Eyes_Cam@20fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
            'Single_Fish_Spontaneous_1@115fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
            'Single_Fish_Spontaneous_2@115fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
            'Single_Fish_Spontaneous_3@115fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
            'Single_Fish_Spontaneous_4@115fps': ['RGB8 (640x480)', 'Y800 (600x380)', 'RGB8 (600x380)'],
            'Single_Fish_Spontaneous_1@30fps': ['RGB8 (640x480)', 'Y800 (600x380)', ]}

f = h5py.File('samples_okr.h5', 'w')

for key, filename in sample_files.items():
    print(key)

    vc = cv2.VideoCapture(filename)
    ret, frame = vc.read()

    if key in f:
        del f[key]

    ds = f.create_dataset(key, shape=(0, *frame.shape), maxshape=(None, *frame.shape), chunks=(1, *frame.shape), compression='lzf', shuffle=True)
    ds.attrs['fps'] = fps[key]
    ds.attrs['formats'] = [s.encode() for s in formats[key]]

    while True:
        ret, frame = vc.read()
        if ret:
            if ds.shape[0] >= 2500:
                break
            ds.resize((ds.shape[0]+1, *ds.shape[1:]))
            ds[-1] = frame[:]
        else:
            break

    print(f'Saved dataset {key} ({ds}), fps {ds.attrs["fps"]}, formats {ds.attrs["formats"]}')

f.close()