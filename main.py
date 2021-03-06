from dataset import load_data
from SVM import runSVM
from selection.Genetic_alg import GA
from selection.variation_based import FFS
from projection.auto_encoder import AE, VAE
from projection.kernel_PCA import kernelPCA
from projection.LDA import LDA
from learning.MDS import myMDS
from learning.tSNE import myTSNE
import numpy as np
import argparse

# params
parser = argparse.ArgumentParser()
parser.add_argument('-m', '--method', default='ae')
parser.add_argument('-d', '--dim', type=int, default=64)
parser.add_argument('-b', '--batch', type=int, default=128)
parser.add_argument('-k', '--kernel', default='linear')
parser.add_argument('--p_c', type=float, default=0)
parser.add_argument('--p_d', type=float, default=1)
parser.add_argument('--g_sigma', type=float, default=1)
parser.add_argument('--s_alpha', type=float, default=1)
parser.add_argument('--s_c', type=float, default=0)
parser.add_argument('--mds_learning', type=bool, default=False)
parser.add_argument('--device', default='cuda:0')
parser.add_argument('--svm_C', type=float, default=10)
parser.add_argument('--svm_k', default="linear")
args = parser.parse_args()

print('Loading data...')
X, X_t, y, y_t = load_data()


def runAE(auto_encoder_dim, inter=512):
    print('Training auto encoder...')
    ae = AE(auto_encoder_dim)
    ae.build(X.shape[1], intermediate_dim=inter)
    ae.auto_encoder.summary()
    ae.fit(X, validation_data=X_t)
    X_ae, Xt_ae = ae.predict(X, X_t)
    score = runSVM(args.svm_C, args.svm_k, X_ae, y, Xt_ae, y_t)
    np.save('data/X_ae', X_ae)
    np.save('data/Xt_ae', Xt_ae)
    with open('result.txt', 'a') as f:
        f.write(f'AE score: {score} (dim={auto_encoder_dim}, kernel={args.svm_k}, C={args.svm_C}, inter={inter})\n')
    return X_ae, Xt_ae


def runVAE(auto_encoder_dim, inter=1024):
    print('Training validation auto encoder...')
    vae = VAE(auto_encoder_dim)
    vae.build(X.shape[1], intermediate_dim=inter)
    vae.auto_encoder.summary()
    vae.fit(X, validation_data=X_t)
    X_vae, Xt_vae = vae.predict(X, X_t)
    score = runSVM(args.svm_C, args.svm_k, X_vae, y, Xt_vae, y_t)
    np.save('data/X_vae', X_vae)
    np.save('data/Xt_vae', Xt_vae)
    with open('result.txt', 'a') as f:
        f.write(f'VAE score: {score} (dim={auto_encoder_dim}, kernel={args.svm_k}, C={args.svm_C}, inter={inter})\n')


def runGA():
    print("Starting GA")
    ga = GA(2048, 10, X, X_t, y, y_t, max_iter=100, IR=0.1)
    mask, score = ga.update()
    with open('result.txt', 'a') as f:
        f.write(f'GA score: {score} (mask={mask}, dim = {mask.sum()}, kernel={args.svm_k}, IR=0.1)\n')


def runFFS(target_dim=200):
    print("starting Forward Feature Selection(On Variance)")
    ffs = FFS(X, X_t, target_dim)
    X_ffs, Xt_ffs = ffs.get_new_features()
    score = runSVM(args.svm_C, args.svm_k, X_ffs, y, Xt_ffs, y_t)
    with open('result.txt', 'a') as f:
        f.write(f'FFS score: {score} (dim={target_dim}, kernel={args.svm_k})\n')


def runKernelPCA(kpca_dim, kernel_name, p_c, p_d, g_sigma, s_alpha, s_c, device):
    print(f"Starting Kernel-[{kernel_name}]-PCA")
    len_train = X.shape[0]
    X_all = np.concatenate([X, X_t], axis=0)
    kpca = kernelPCA(X_all, kpca_dim, device, kernel_name, p_c, p_d, g_sigma, s_alpha, s_c)
    X_kpca_all = kpca.compute()
    X_kpca, Xt_kpca = X_kpca_all[:len_train], X_kpca_all[len_train:]
    score = runSVM(args.svm_C, args.svm_k, X_kpca, y, Xt_kpca, y_t)
    with open('result.txt', 'a') as f:
        f.write(f'Kernal-[{kernel_name},p_c={p_c},p_d={p_d},g_sigma={g_sigma},s_alpha={s_alpha},'
                f's_c={s_c}]-PCA score: {score} (dim={kpca_dim}, kernel={args.svm_k},)\n')


def runLDA(lda_dim, device):
    print("Starting LDA")
    lda = LDA(X, lda_dim, y, X.shape[1], device, 50)
    X_lda, Xt_lda = lda.compute(X, X_t)
    score = runSVM(args.svm_C, args.svm_k, X_lda, y, Xt_lda, y_t)
    with open('result.txt', 'a') as f:
        f.write(f'LDA score: {score} (dim={lda_dim}, kernel={args.svm_k})\n')


def runMDS(mds_dim, mds_learning, device):
    print("Starting MDS")
    len_train = X.shape[0]
    X_all = np.concatenate([X, X_t], axis=0)
    mds = myMDS(data=X_all, dim=mds_dim, tol=1e-6, lr=1e-1, max_iter=100, device=device, learning=mds_learning)
    X_mds_all = mds.compute()
    X_mds, Xt_mds = X_mds_all[:len_train], X_mds_all[len_train:]
    score = runSVM(args.svm_C, args.svm_k, X_mds, y, Xt_mds, y_t)
    flag = "learning" if mds_learning else "non-learning"
    with open('result.txt', 'a') as f:
        f.write(f'MDS[{flag}] score: {score} (dim={mds_dim}, kernel={args.svm_k})\n')


def runTSNE(tsne_dim, device):
    print("Starting TSNE")
    len_train = X.shape[0]
    X_all = np.concatenate([X[:len_train], X_t], axis=0)
    tsne = myTSNE(data=X_all, dim=tsne_dim, tol=1e-6, lr=1e-1, max_iter=100, device=device)
    X_tsne_all = tsne.compute()
    X_tsne, Xt_tsne = X_tsne_all[:len_train], X_tsne_all[len_train:]
    score = runSVM(args.svm_C, args.svm_k, X_tsne, y, Xt_tsne, y_t)
    with open('result.txt', 'a') as f:
        f.write(f'TSNE score: {score} (dim={tsne_dim}, kernel={args.svm_k})\n')


if __name__ == '__main__':
    if args.method == 'ae':
        runAE(args.dim)
    elif args.method == 'vae':
        runVAE(args.dim)
    elif args.method == 'ga':
        runGA()
    elif args.method == 'ffs':
        runFFS()
    elif args.method == 'kpca':
        runKernelPCA(args.dim, args.kernel, args.p_c, args.p_d, args.g_sigma, args.s_alpha, args.s_c, args.device)
    elif args.method == "lda":
        runLDA(args.dim, args.device)
    elif args.method == "mds":
        runMDS(args.dim, args.mds_learning, args.device)
    elif args.method == "tsne":
        runTSNE(args.dim, args.device)
