"""

"""

import math
import torch 
import torch.nn.functional as F
from torch_geometric.data import DataLoader
from torch_geometric.nn import GCNConv, ChebConv, SAGEConv, GraphConv, DenseSAGEConv, dense_diff_pool, DenseGCNConv
from torch_geometric.nn import TopKPooling, SAGPooling, EdgePooling
from torch.nn import Linear, Dropout, PReLU, Conv2d, MaxPool2d, AvgPool2d, BatchNorm2d
from torch_geometric.utils import to_dense_batch, to_dense_adj, dense_to_sparse

#device = torch.device('cuda', 0)

class SCG(torch.nn.Module):
    """Self-organized Graph Construction Module
    Args:
        in_features: size of each input sample
        bn_features: size of bottleneck layer
        out_features: size of each output sample
        topk: size of top k-largest connections of each channel
    """
    def __init__(self, in_features: int, bn_features: int, out_features: int, topk: int):
        super().__init__()

        self.channels = 126
        self.in_features = in_features
        self.bn_features = bn_features
        self.out_features = out_features
        self.topk = topk
        
        self.bnlin = Linear(in_features, bn_features)
        self.gconv = DenseGCNConv(in_features, out_features)
        
    def forward(self, x): 

        x = x.reshape(-1, self.channels, self.in_features)
        xa = torch.tanh(self.bnlin(x))
        adj = torch.matmul(xa, xa.transpose(2,1))
        adj = torch.softmax(adj, 2)
        amask = torch.zeros(xa.size(0), self.channels, self.channels)#.to(device)
        amask.fill_(0.0)
        s, t = adj.topk(self.topk, 2)
        amask.scatter_(2, t, s.fill_(1))
        adj = adj*amask
        x = F.relu(self.gconv(x, adj)) 
        
        return x
    
class ST_SCGNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        
        drop_rate = 0.1
        topk = 20
        self.channels = 126

        self.conv0 = Conv2d(1, 32, (4, 7))
        self.drop0 = Dropout(drop_rate)
        self.pool0 = MaxPool2d((1, 2))
        self.scg0 = SCG(4 * 32, 64, 32, topk)
        
        self.conv1 = Conv2d(1, 32, (4,5))
        self.drop1 = Dropout(drop_rate)
        self.pool1 = MaxPool2d((1,2))
        self.scg1 = SCG(6*32, 64, 32, topk)
        
        self.conv2 = Conv2d(1, 32, (4,3))
        self.drop2 = Dropout(drop_rate)
        self.pool2 = MaxPool2d((1,2))
        self.scg2 = SCG(8*32, 64, 32, topk)
        
        self.conv3 = Conv2d(64, 128, (4,1))
        self.drop3 = Dropout(drop_rate)
        self.pool3 = MaxPool2d((1,2))
        self.scg3 = SCG(10*32, 64, 32, topk)

        self.drop4 = Dropout(drop_rate)

        self.linend = Linear(self.channels*32*4, 3)

        
    def forward(self, x, edge_index, batch): 
        
        x, mask = to_dense_batch(x, batch)

        x = x.reshape(-1, 1, 4, 10)

        x00 = F.relu(self.conv0(x))
        x00 = self.drop0(x00)
        x00 = self.pool0(x00)

        x0 = self.scg0(x00)
        
        x = F.relu(self.conv1(x))
        x = self.drop1(x)
        x = self.pool1(x)
        
        x1 = self.scg1(x)
        
        x = F.relu(self.conv2(x)) 
        x = self.drop2(x)
        x = self.pool2(x)
        
        x2 = self.scg2(x)
        
        x = F.relu(self.conv3(x))
        x = self.drop3(x)
        x = self.pool3(x)

        x3 = self.scg3(x)
        
        x = torch.cat([x0,x1, x2, x3], dim=1)
        x = self.drop4(x)

        x = x.reshape(-1, self.channels*32*4)
        x = self.linend(x)
        pred = F.softmax(x,1) 
        
        return x, pred
        
    