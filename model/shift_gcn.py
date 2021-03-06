import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import numpy as np
import math
from .layers import GraphAttentionLayer, SpGraphAttentionLayer
import sys
sys.path.append("./model/Temporal_shift/")

from cuda.shift import Shift


def import_class(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def conv_init(conv):
    nn.init.kaiming_normal(conv.weight, mode='fan_out')
    nn.init.constant(conv.bias, 0)


def bn_init(bn, scale):
    nn.init.constant(bn.weight, scale)
    nn.init.constant(bn.bias, 0)


class tcn(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=9, stride=1):
        super(tcn, self).__init__()
        pad = int((kernel_size - 1) / 2)
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=(kernel_size, 1), padding=(pad, 0),
                              stride=(stride, 1))

        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU()
        conv_init(self.conv)
        bn_init(self.bn, 1)

    def forward(self, x):
        x = self.bn(self.conv(x))
        return x


class Shift_tcn(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=9, stride=1):
        super(Shift_tcn, self).__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels

        self.bn = nn.BatchNorm2d(in_channels)
        self.bn2 = nn.BatchNorm2d(in_channels)
        bn_init(self.bn2, 1)
        self.relu = nn.ReLU(inplace=True)
        self.shift_in = Shift(channel=in_channels, stride=1, init_scale=1)
        self.shift_out = Shift(channel=out_channels, stride=stride, init_scale=1)

        self.temporal_linear = nn.Conv2d(in_channels, out_channels, 1)
        nn.init.kaiming_normal(self.temporal_linear.weight, mode='fan_out')

    def forward(self, x):
        
        x = self.bn(x)
        # shift1
        x = self.shift_in(x)
        x = self.temporal_linear(x)
        x = self.relu(x)
        # shift2
        x = self.shift_out(x)
        x = self.bn2(x)
        return x


class Shift_gcn(nn.Module):
    def __init__(self, in_channels, out_channels, A, coff_embedding=4, num_subset=3):
        super(Shift_gcn, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        # print("in")
        # print(in_channels)
        # print(out_channels)
        # print("out")
        if in_channels != out_channels:
            self.down = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.down = lambda x: x

        self.Linear_weight = nn.Parameter(torch.zeros(in_channels, out_channels, requires_grad=True, device='cuda'), requires_grad=True)
        nn.init.normal_(self.Linear_weight, 0,math.sqrt(1.0/out_channels))

        self.Linear_bias = nn.Parameter(torch.zeros(1,1,out_channels,requires_grad=True,device='cuda'),requires_grad=True)
        nn.init.constant(self.Linear_bias, 0)

        self.Feature_Mask = nn.Parameter(torch.ones(1,25,in_channels, requires_grad=True,device='cuda'),requires_grad=True)
        nn.init.constant(self.Feature_Mask, 0)

        self.bn = nn.BatchNorm1d(25*out_channels)
        self.relu = nn.ReLU()

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                conv_init(m)
            elif isinstance(m, nn.BatchNorm2d):
                bn_init(m, 1)

        index_array = np.empty(25*in_channels).astype(np.int)
        for i in range(25):
            for j in range(in_channels):
                index_array[i*in_channels + j] = (i*in_channels + j + j*in_channels)%(in_channels*25)
        self.shift_in = nn.Parameter(torch.from_numpy(index_array),requires_grad=False)

        index_array = np.empty(25*out_channels).astype(np.int)
        for i in range(25):
            for j in range(out_channels):
                index_array[i*out_channels + j] = (i*out_channels + j - j*out_channels)%(out_channels*25)
        self.shift_out = nn.Parameter(torch.from_numpy(index_array),requires_grad=False)
        
        # self.attentions = [GraphAttentionLayer(f_len, int(f_len/8), dropout=0.6, alpha=0.3, concat=True) for _ in range(6)]
        # for i, attention in enumerate(attentions):
        #     self.add_module('attention_{}'.format(i), attention)
        # print(f"the shape of in{self.shift_in.shape}")
        # print(f"the shape of out{self.shift_out.shape}")

    def forward(self, x0):
        # print("+")
        # print(x0.shape)
        # print("+")
        n, c, t, v = x0.size()
        # n batch
        # c ?????????
        # t ??????
        # v ?????????
        # x_attention = x0.view(n,c,t*v).permute(0,2,1).contiguous() # n node f
        # bat,node,f_len = x_attention.size()
        # attentions = [GraphAttentionLayer(f_len, int(f_len/8), dropout=0.6, alpha=0.3, concat=True) for _ in range(6)]
        # for i, attention in enumerate(attentions):
        #     self.add_module('attention_{}'.format(i), attention)
       
        x = x0.permute(0,2,3,1).contiguous()

        # shift1
        x = x.view(n*t,v*c)
        # print("+")
        # print(x.shape)
        # print("+")
        x = torch.index_select(x, 1, self.shift_in)
        x = x.view(n*t,v,c) # 
       # print(f"x shape is t_{x.shape}")
        x2 = x.view(n,t,v,c) # 4 100 25 4
        
        t_ = torch.sum(x2,-1) # 4 300 3
        temp = t_.size()
       # print(f"t_ shape is t_{t_.shape}")
        attentions = [GraphAttentionLayer(n,temp[-1], (int((temp[-1])/2)+1), dropout=0.6, alpha=0.3, concat=True) for _ in range(1)]
        # for i, attention in enumerate(attentions):
        #     self.add_module('attention_{}'.format(i), attention)
            
        out_att = GraphAttentionLayer(n,(int((temp[-1])/2)+1)*1, temp[-1], dropout=0.6, alpha=0.3, concat=False)
      
        x_att = torch.cat([att(t_, torch.ones(temp[1],temp[1]).cuda()) for att in attentions], dim=2)
        out_att = out_att(x_att,torch.ones(temp[1],temp[1]).cuda())
        
        size_out = out_att.size()
        out_att = out_att.view(size_out[0]*size_out[1],size_out[2],1)
        #print(f"out_att shape is t_{out_att.shape}")
        x = torch.mul(out_att,x)
        x = x * (torch.tanh(self.Feature_Mask)+1)
        
        
        x = torch.einsum('nwc,cd->nwd', (x, self.Linear_weight)).contiguous() # nt,v,c
        x = x + self.Linear_bias

        # shift2
        x = x.view(n*t,-1) 
        x = torch.index_select(x, 1, self.shift_out)
        x = self.bn(x)
        x = x.view(n,t,v,self.out_channels).permute(0,3,1,2) # n,c,t,v

        x = x + self.down(x0)
        x = self.relu(x)
        return x


class TCN_GCN_unit(nn.Module):
    def __init__(self, in_channels, out_channels, A, stride=1, residual=True):
        super(TCN_GCN_unit, self).__init__()
        self.gcn1 = Shift_gcn(in_channels, out_channels, A)
        self.tcn1 = Shift_tcn(out_channels, out_channels, stride=stride)
        self.relu = nn.ReLU()

        if not residual:
            self.residual = lambda x: 0

        elif (in_channels == out_channels) and (stride == 1):
            self.residual = lambda x: x
        else:
            self.residual = tcn(in_channels, out_channels, kernel_size=1, stride=stride)

    def forward(self, x):
        x = self.tcn1(self.gcn1(x)) + self.residual(x)
        return self.relu(x)


class Model(nn.Module):
    def __init__(self, num_class=60, num_point=25, num_person=2, graph=None, graph_args=dict(), in_channels=3):
        super(Model, self).__init__()

        if graph is None:
            raise ValueError()
        else:
            Graph = import_class(graph)
            self.graph = Graph(**graph_args)

        A = self.graph.A
        self.data_bn = nn.BatchNorm1d(num_person * in_channels * num_point)

        self.l1 = TCN_GCN_unit(3, 64, A, residual=False)
        self.l2 = TCN_GCN_unit(64, 64, A)
        self.l3 = TCN_GCN_unit(64, 64, A)
        self.l4 = TCN_GCN_unit(64, 64, A)
        self.l5 = TCN_GCN_unit(64, 128, A, stride=2)
        self.l6 = TCN_GCN_unit(128, 128, A)
        self.l7 = TCN_GCN_unit(128, 128, A)
        self.l8 = TCN_GCN_unit(128, 256, A, stride=2)
        self.l9 = TCN_GCN_unit(256, 256, A)
        self.l10 = TCN_GCN_unit(256, 256, A)

        self.fc = nn.Linear(256, num_class)
        nn.init.normal(self.fc.weight, 0, math.sqrt(2. / num_class))
        bn_init(self.data_bn, 1)

    def forward(self, x):
        N, C, T, V, M = x.size()

        x = x.permute(0, 4, 3, 1, 2).contiguous().view(N, M * V * C, T)
        x = self.data_bn(x)
        x = x.view(N, M, V, C, T).permute(0, 1, 3, 4, 2).contiguous().view(N * M, C, T, V)

        x = self.l1(x)
        x = self.l2(x)
        x = self.l3(x)
        x = self.l4(x)
        x = self.l5(x)
        x = self.l6(x)
        x = self.l7(x)
        x = self.l8(x)
        x = self.l9(x)
        x = self.l10(x)

        # N*M,C,T,V
        c_new = x.size(1)
        x = x.view(N, M, c_new, -1)
        x = x.mean(3).mean(1)

        return self.fc(x)
