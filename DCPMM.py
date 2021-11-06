import numpy as np
import cupy as cp
import time as time
import math
from scipy.io import mmread
from multiprocessing import Pool, cpu_count
from numba import jit, njit, prange, cuda
from scipy.linalg import blas as FB
from pynvml import *

def MatrixMultiply(A,B,c):
    m,n = A.shape
    if m <= c: #base case we dont need to partition
        A = cp.array(A)
        B = cp.array(B)
        return cp.matmul(A,B)
    return Partition(A,B,c)

def Partition(A,B,c):
    m,n = A.shape
    n,p = B.shape
    #h = nvmlDeviceGetHandleByIndex(0)
    info = nvmlDeviceGetMemoryInfo(h)
    #if (15 * m**2 < info.free):
    if (((m*n) + (n*p)) * 8 < info.free):
        #maybe time these
        return PartitionGPU(A,B,c)
    else:
        return PartitionCPU(A,B,c)

def PartitionGPU(A,B,c):
    m,n = A.shape
    #print("GPU")
    if (type(A) == np.ndarray):
        A = cp.array(A)
        B = cp.array(B)
    if m <= n:
        #axis 0 = rows, axis 1 = columns
        [A1,A2] = cp.array_split(A, 2, axis=1)
        [B1,B2] = cp.array_split(B, 2, axis=0)
        C1 = cp.array(MatrixMultiply(A1,B1,c))
        del A1
        del B1
        C2 = cp.array(MatrixMultiply(A2,B2,c))
        del A2
        del B2
        return C1 + C2

        #return cp.array(MatrixMultiply(A1,B1,c)) + cp.array(MatrixMultiply(A2,B2,c))
    else: #m>n
        [A1,A2] = cp.array_split(A, 2, axis=0)
        [B1,B2] = cp.array_split(B, 2, axis=1)

        C1 = MatrixMultiply(A1,B1,c)
        C2 = MatrixMultiply(A1,B2,c)
        C12 = cp.hstack((C1,C2))
        del C1
        del C2

        C3 = MatrixMultiply(A2,B1,c)
        C4 = MatrixMultiply(A2,B2,c)
        C34 = cp.hstack((C3,C4))
        del C3
        del C4
        return cp.vstack((C12,C34))

def PartitionCPU(A,B,c):
    m,n = A.shape
    #print("CPU")
    if (type(A) == cp.ndarray):
        A = cp.asnumpy(A)
        B = cp.asnumpy(B)
    if m <= n:
        #axis 0 = rows, axis 1 = columns
        [A1,A2] = np.array_split(A, 2, axis=1)
        [B1,B2] = np.array_split(B, 2, axis=0)
        C = cp.asnumpy(MatrixMultiply(A1,B1,c)) + cp.asnumpy(MatrixMultiply(A2,B2,c))
        return C
    else: #m>n
        [A1,A2] = np.array_split(A, 2, axis=0)
        [B1,B2] = np.array_split(B, 2, axis=1)
        C1 = cp.asnumpy(MatrixMultiply(A1,B1,c))
        C2 = cp.asnumpy(MatrixMultiply(A1,B2,c))
        C3 = cp.asnumpy(MatrixMultiply(A2,B1,c))
        C4 = cp.asnumpy(MatrixMultiply(A2,B2,c))
        
        C12 = np.hstack((C1,C2))
        C34 = np.hstack((C3,C4))
        C = np.vstack((C12,C34))
        return C

def numpyMult(A,B):
    return np.dot(A,B)

def cupyMult(A,B):
    A = cp.array(A)
    B = cp.array(B)
    return cp.matmul(A,B)

if __name__ == "__main__":
    nvmlInit()
    h = nvmlDeviceGetHandleByIndex(0)
    info = nvmlDeviceGetMemoryInfo(h)
    #print(info.free)
    partitionLimit = math.sqrt(info.free / (8)) / 2
    #print(partitionLimit)

    row = 20000
    col = 20000
    testNums = [10, 20, 50, 80, 100, 150, 200, 300]
    np.random.seed(42)

    A = np.random.randint(10, size=(row, col))
    B = np.random.randint(10, size=(row, col))
    cores = cpu_count()
    
    print("Rows:", row)
    print("Cols:", col)
    print("Cores:", cores)
    print("A:\n", A)
    print("B:\n", B)

    start = time.time()
    result = MatrixMultiply(A,B,partitionLimit)
    end = time.time()
    print("C:\n",result)
    print("Our Algorithm")
    print("Time Taken:", end - start)

    #start = time.time()
    #temp = numpyMult(A.astype(float),B.astype(float))
    #end = time.time()
    #print("C:\n",temp)
    #print("Numpy MM")
    #print("Time Taken:", end - start)

    # start = time.time()
    # temp = cupyMult(A,B)
    # end = time.time()
    # print("C:\n",temp)
    # print("Cupy MM")
    # print("Time Taken:", end - start)

    print()
    print("Reading Matrix File Test")
    fileName = 'datasets/494_bus.mtx'
    mat = mmread(fileName)        #reads the mtx file
    A = mat.todense(None,None)    #changes the matrix type to numpy.matrix
    A = cp.array(A)
    B = cp.array(A)
    row,col = A.shape
    print("Rows:", row)
    print("Cols:", col)
    print("Cores:", cores)
    print("A:\n", A)
    print("B:\n", B)
    start = time.time()
    result = MatrixMultiply(A,B,row/cores)
    end = time.time()
    print("C:\n",result)
    print("Time Taken:", end - start)