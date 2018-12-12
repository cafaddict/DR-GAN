#!/usr/bin/env python
# encoding: utf-8


import os
import argparse
import datetime
import glob
import numpy as np
import torch
from torch import nn, optim
from torch.autograd import Variable
from model import single_DR_GAN_model as single_model
from model import multiple_DR_GAN_model as multi_model
from util.create_randomdata import create_randomdata
from util.DataAugmentation import ResizeDemo
from train_single_DRGAN import train_single_DRGAN
from train_multiple_DRGAN import train_multiple_DRGAN
from skimage import io, transform
from tqdm import tqdm
from Generate_Image import Generate_Image
import pdb


def DataLoader(image_dir):
    """
    Define dataloder which is applicable to your data
    
    ### ouput
    images : 4 dimension tensor (the number of image x channel x image_height x image_width)
             BGR [-1,1]
    id_labels : one-hot vector with Nd dimension
    pose_labels : one-hot vetor with Np dimension
    Nd : the nuber of ID in the data
    Np : the number of discrete pose in the data
    Nz : size of noise vector (Default in the paper is 50)
    """
    # Nd = []
    # Np = []
    # Nz = []
    # channel_num = []
    # images = []
    # id_labels = []
    # pose_labels = []

    # Demo
    # image_dir = "cfp-dataset/Data/Images/"
    rsz = ResizeDemo(110)

    images = np.zeros((7000, 110, 110, 3))
    id_labels = np.zeros(7000)
    pose_labels = np.zeros(7000)
    count = 0
    gray_count = 0
    with open('test_posetemp_imglist.txt') as f:
        for line in f:
            img_path = os.path.join('test/', line)
            print(img_path)
            img = io.imread(img_path)
            if len(img.shape)==2:
                gray_count = gray_count+1
                continue
            print("555")
            img_rsz = rsz(img)
            images[count] = img_rsz
            id_labels[count] = line.split("/")[0]
            pose_labels[count] = ((count % 30) // 10) / 2
            print([id_labels[count], pose_labels[count]])
            count = count + 1


    id_labels = id_labels.astype('int64')
    pose_labels = pose_labels.astype('int64')

    #[0,255] -> [-1,1]
    images = images *2 - 1
    # RGB -> BGR
    images = images[:,:,:,[2,1,0]]
    # B x H x W x C-> B x C x H x W
    images = images.transpose(0, 3, 1, 2)

    images = images[:gray_count*-1]
    id_labels = id_labels[:gray_count*-1]
    pose_labels = pose_labels[:gray_count*-1]
    Nd = int(id_labels.max() + 1)
    Np = int(pose_labels.max() + 1)
    Nz = 50
    channel_num = 3

    return [images, id_labels, pose_labels, Nd, Np, Nz, channel_num]


if __name__=="__main__":

    parser = argparse.ArgumentParser(description='DR_GAN')
    # learning & saving parameterss
    parser.add_argument('-lr', type=float, default=0.0002, help='initial learning rate [default: 0.0002]')
    parser.add_argument('-beta1', type=float, default=0.5, help='adam optimizer parameter [default: 0.5]')
    parser.add_argument('-beta2', type=float, default=0.999, help='adam optimizer parameter [default: 0.999]')
    parser.add_argument('-epochs', type=int, default=1000, help='number of epochs for train [default: 1000]')
    parser.add_argument('-batch-size', type=int, default=8, help='batch size for training [default: 8]')
    parser.add_argument('-save-dir', type=str, default='snapshot', help='where to save the snapshot')
    parser.add_argument('-save-freq', type=int, default=1, help='save learned model for every "-save-freq" epoch')
    parser.add_argument('-cuda', action='store_true', default=False, help='enable the gpu')
    # data souce
    parser.add_argument('-random', action='store_true', default=False, help='use randomely created data to run program')
    parser.add_argument('-data-place', type=str, default='./data', help='prepared data path to run program')
    # model
    parser.add_argument('-multi-DRGAN', action='store_true', default=False, help='use multi image DR_GAN model')
    parser.add_argument('-images-perID', type=int, default=0, help='number of images per person to input to multi image DR_GAN')
    # option
    parser.add_argument('-snapshot', type=str, default=None, help='filename of model snapshot(snapshot/{Single or Multiple}/{date}/{epoch}) [default: None]')
    parser.add_argument('-generate', action='store_true', default=None, help='Generate pose modified image from given image')

    args = parser.parse_args()

    # update args and print
    if args.multi_DRGAN:
        args.save_dir = os.path.join(args.save_dir, 'Multi',datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    else:
        args.save_dir = os.path.join(args.save_dir, 'Single',datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))

    os.makedirs(args.save_dir)

    print("Parameters:")
    for attr, value in sorted(args.__dict__.items()):
        text ="\t{}={}\n".format(attr.upper(), value)
        print(text)
        with open('{}/Parameters.txt'.format(args.save_dir),'a') as f:
            f.write(text)


    # input data
    if args.random:
        images, id_labels, pose_labels, Nd, Np, Nz, channel_num = create_randomdata()
    else:
        print('n\Loading data from [%s]...' % args.data_place)
        try:
            images, id_labels, pose_labels, Nd, Np, Nz, channel_num = DataLoader(args.data_place)
        except:
            print("Sorry, failed to load data")

    # model
    if args.snapshot is None:
        if not(args.multi_DRGAN):
            D = single_model.Discriminator(Nd, Np, channel_num)
            G = single_model.Generator(Np, Nz, channel_num)
        else:
            if args.images_perID==0:
                print("Please specify -images-perID of your data to input to multi_DRGAN")
                exit()
            else:
                D = multi_model.Discriminator(Nd, Np, channel_num)
                G = multi_model.Generator(Np, Nz, channel_num, args.images_perID)
    else:
        print('\nLoading model from [%s]...' % args.snapshot)
        try:
            D = torch.load('{}_D.pt'.format(args.snapshot))
            G = torch.load('{}_G.pt'.format(args.snapshot))
        except:
            print("Sorry, This snapshot doesn't exist.")
            exit()

    if not(args.generate):
        if not(args.multi_DRGAN):
            train_single_DRGAN(images, id_labels, pose_labels, Nd, Np, Nz, D, G, args)
        else:
            if args.batch_size % args.images_perID == 0:
                train_multiple_DRGAN(images, id_labels, pose_labels, Nd, Np, Nz, D, G, args)
            else:
                print("Please give valid combination of batch_size, images_perID")
                exit()
    else:
        # pose_code = [] # specify arbitrary pose code for every image
        pose_code = np.random.uniform(-1,1, (images.shape[0], Np))
        features = Generate_Image(images, pose_code, Nz, G, args)
