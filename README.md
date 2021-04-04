# It base Shift-GCN that adds GAT module
## The version is v2.0            -- Moule Lin
It exceeds state-of-the-art methods with 10x less FLOPs.



## Compile cuda extensions

  ```
  cd ./model/Temporal_shift
  bash run.sh
  ```

## Data Preparation

 - Download the raw data of [NTU-RGBD](https://github.com/shahroudy/NTURGB-D) and [NTU-RGBD120](https://github.com/shahroudy/NTURGB-D). Put NTU-RGBD data under the directory `./data/nturgbd_raw`. Put NTU-RGBD120 data under the directory `./data/nturgbd120_raw`. 
 
 - For NTU-RGBD, preprocess data with `python data_gen/ntu_gendata.py`. For NTU-RGBD120, preprocess data with `python data_gen/ntu120_gendata.py`. 
  
 - Generate the bone data with `python data_gen/gen_bone_data.py`.

 - Generate the motion data with `python data_gen/gen_motion_data.py`.

## Training & Testing

  - NTU X-view

    `python main.py --config ./config/nturgbd-cross-view/train_joint.yaml`

    `python main.py --config ./config/nturgbd-cross-view/train_bone.yaml`

    `python main.py --config ./config/nturgbd-cross-view/train_joint_motion.yaml`

    `python main.py --config ./config/nturgbd-cross-view/train_bone_motion.yaml`

  - NTU X-sub

    `python main.py --config ./config/nturgbd-cross-subject/train_joint.yaml`

    `python main.py --config ./config/nturgbd-cross-subject/train_bone.yaml`

    `python main.py --config ./config/nturgbd-cross-subject/train_joint_motion.yaml`

    `python main.py --config ./config/nturgbd-cross-subject/train_bone_motion.yaml`

  - For NTU120, change the dataset path in config files, and change `num_class` in config files from 60 to 120.
  
