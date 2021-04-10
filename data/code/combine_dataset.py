import os
import argparse
import pandas as pd
import numpy as np


# 把分散的结果汇总起来
def combine_datasets(data_path):
    dfs = []
    for i in range(0, 16):
        dfs.append(pd.read_csv(os.path.join(data_path, 'train_{}.csv'.format(i))).set_index('id'))
        os.remove(os.path.join(data_path, 'train_{}.csv'.format(i)))
    train = pd.concat(dfs)
    train.to_csv(os.path.join(data_path, 'train.csv'.format()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="../user_data", help="path of output file")
    args = parser.parse_args()

    output_dir = args.output

    combine_datasets(output_dir)
