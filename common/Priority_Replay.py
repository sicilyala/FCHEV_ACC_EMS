#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 25 00:43:00 2018

@author: wuyuankai
"""

import numpy as np


class SumTree(object):
    """
    This SumTree code is modified version and the original code is from: 
    https://github.com/jaara/AI-blog/blob/master/SumTree.py
    Story the data with it priority in tree and data frameworks.
    """
    data_pointer = 0

    def __init__(self, capacity):
        self.capacity = capacity  # for all priority values
        self.tree = np.zeros(2 * capacity - 1)
        # [--------------Parent nodes-------------][-------leaves to recode priority-------]
        #             size: capacity - 1                       size: capacity
        self.data = np.zeros(capacity, dtype=object)  # for all transitions
        # [--------------data frame-------------]
        #             size: capacity

    def add(self, p, data):
        tree_idx = self.data_pointer + self.capacity - 1
        self.data[self.data_pointer] = data  # update data_frame
        self.update(tree_idx, p)  # update tree_frame

        self.data_pointer += 1
        if self.data_pointer >= self.capacity:  # replace when exceed the capacity
            self.data_pointer = 0

    def update(self, tree_idx, p):
        change = p - self.tree[tree_idx]
        self.tree[tree_idx] = p
        # then propagate the change through tree
        while tree_idx != 0:  # this method is faster than the recursive loop in the reference code
            tree_idx = (tree_idx - 1) // 2
            self.tree[tree_idx] += change

    def get_leaf(self, v):
        """
        Tree structure and array storage:
        Tree index:
             0         -> storing priority sum
            / \
          1     2
         / \   / \
        3   4 5   6    -> storing priority for transitions
        Array type for storing:
        [0,1,2,3,4,5,6]
        """
        parent_idx = 0
        while True:  # the while loop is faster than the method in the reference code
            cl_idx = 2 * parent_idx + 1  # this leaf's left and right kids
            cr_idx = cl_idx + 1
            if cl_idx >= len(self.tree):  # reach bottom, end search
                leaf_idx = parent_idx
                break
            else:  # downward search, always search for a higher priority node
                if v <= self.tree[cl_idx]:
                    parent_idx = cl_idx
                else:
                    v -= self.tree[cl_idx]
                    parent_idx = cr_idx

        data_idx = leaf_idx - self.capacity + 1
        # tree_index, 权重值, 对应的数据
        return leaf_idx, self.tree[leaf_idx], self.data[data_idx]

    @property
    def total_p(self):
        return self.tree[0]  # the root     # 所有叶子值的和


class Memory_PER(object):  # stored as ( s, a, r, s_ ) in SumTree
    """
    This SumTree code is modified version and the original code is from:
    https://github.com/jaara/AI-blog/blob/master/Seaquest-DDQN-PER.py
    """
    epsilon = 1e-6  # small amount to avoid zero priority
    alpha = 0.6  # [0~1] convert the importance of TD error to priority
    beta = 0.4  # importance-sampling, from initial value increasing to 1 at end
    beta_increment_per_sampling = 0.001
    abs_err_upper = 1.  # clipped abs error

    def __init__(self, args):
        capacity = int(args.buffer_size)
        self.tree = SumTree(capacity)
        self.capacity = capacity
        self.batch_size = int(args.batch_size)
        self.counter = 0
        self.currentSize = 0

    def store(self, transition):
        max_p = np.max(self.tree.tree[-self.tree.capacity:])        # 找到最大的权值
        if max_p == 0:                                              # 该数据的初始值np.zeros
            max_p = self.abs_err_upper
        self.tree.add(max_p, transition)  # set the max p for new data  why ? 保证所有transition都至少被重放一次
        self.counter += 1
        self.currentSize = min(self.capacity, self.counter)

    def sample(self):
        n = self.batch_size
        b_idx = np.empty((n,), dtype=np.int32)
        b_memory = np.empty((n, self.tree.data[0].size), dtype=np.float32)
        ISWeights = np.empty((n, 1), dtype=np.float32)
        
        pri_seg = self.tree.total_p / n  # priority segment
        self.beta = np.min([1., self.beta + self.beta_increment_per_sampling])  # max = 1

        min_prob = np.min(self.tree.tree[-self.tree.capacity:]) / self.tree.total_p  # for later calculate ISweight
        min_prob = max(min_prob, self.epsilon)  # in case min_prob==0
        
        for i in range(n):
            a, b = pri_seg * i, pri_seg * (i + 1)
            v = np.random.uniform(a, b)
            idx, p, data = self.tree.get_leaf(v)        # 权值
            p = max(p, self.epsilon)                    # in case p==0
            prob = p / self.tree.total_p                # 权值占整体的比例，即概率
            ISWeights[i, 0] = np.power(prob / min_prob, -self.beta)
            b_idx[i], b_memory[i, :] = idx, data
        return b_idx, b_memory, ISWeights

    def batch_update(self, tree_idx, abs_errors):
        abs_errors += self.epsilon  # convert to abs and avoid 0
        clipped_errors = np.minimum(abs_errors, self.abs_err_upper)
        ps = np.power(clipped_errors, self.alpha)
        for ti, p in zip(tree_idx, ps):
            self.tree.update(ti, p)
