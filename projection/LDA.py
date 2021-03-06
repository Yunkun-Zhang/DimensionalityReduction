import numpy as np
import torch
import scipy


class LDA:
    def __init__(self, data, dim, labels, ori_dim=2048, device="cuda:0", classes=50):
        self.device = device
        self.data = torch.tensor(data).to(self.device)
        self.dim = dim
        self.labels = labels
        self.classes = classes
        self.ori_dim = ori_dim
        assert dim <= data.shape[1]

    def _process_data(self):
        self.global_mu = torch.mean(self.data, dim=0).to(self.device)
        self.parts = [torch.empty([0, self.ori_dim]).to(self.device) for _ in range(self.classes)]
        for feature, label in zip(self.data, self.labels):
            self.parts[label - 1] = torch.cat(
                [self.parts[label - 1], feature.view(1, -1)], dim=0)
        self.local_mus = [torch.mean(x, dim=0) for x in self.parts]

    def compute(self, X, X_t):
        self._process_data()
        S_w = torch.zeros([self.ori_dim, self.ori_dim]).to(self.device)
        S_b = torch.zeros([self.ori_dim, self.ori_dim]).to(self.device)
        for i in range(self.classes):
            S_b += self.parts[i].shape[0] * \
                   torch.mm((self.local_mus[i] - self.global_mu).view(-1, 1),
                            (self.local_mus[i] - self.global_mu).view(1, -1))

            S_w += torch.mm((self.parts[i] - self.local_mus[i]).t(),
                            (self.parts[i] - self.local_mus[i]))
        print("S_w,S_b done.")
        S_wm1S_b = torch.mm(torch.pinverse(S_w), S_b)
        print("S_w^(-1)S_b done.")
        e_vals, e_vecs = torch.lobpcg(S_wm1S_b, self.dim, largest=True)
        print("Eigenvalue decomposition done.")

        X = torch.tensor(X).type_as(e_vecs).to(self.device)
        X_t = torch.tensor(X_t).type_as(e_vecs).to(self.device)

        return torch.mm(X, e_vecs).to("cpu").numpy(), torch.mm(X_t, e_vecs).to("cpu").numpy(),


if __name__ == "__main__":
    pass
