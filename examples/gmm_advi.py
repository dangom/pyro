import json
import torch
import pyro
import pyro.distributions as dist
from pyro.distributions.util import log_sum_exp
from torch.distributions import constraints, transform_to
from pyro.infer import SVI
from pyro import poutine
from pyro.contrib.autoguide import (ADVIDiagonalNormal, ADVIDiscreteParallel,
                                    ADVIMaster, ADVIMultivariateNormal)
import pyro.optim as optim
from pdb import set_trace as bb


def model(K, alpha0, y):
    theta = pyro.sample("theta", dist.Dirichlet(alpha0 * torch.ones(K)))
    mu = pyro.sample("mu", dist.Normal(torch.zeros(K, y.shape[-1]), 10. * torch.ones(K, y.shape[-1])))
    sigma = pyro.sample("sigma", dist.LogNormal(torch.ones(K, y.shape[-1]), torch.ones(K, y.shape[-1])))
    # sigma = transform_to(dist.Normal.arg_constraints['scale'])(sigma)

    with pyro.iarange('data', len(y)):
        assign = pyro.sample('mixture', dist.Categorical(theta))
        pyro.sample('obs', dist.Normal(mu[assign], sigma[assign]), obs=y[assign])


def get_data(fname, varnames):
    with open(fname, "r") as f:
        j = json.load(f)
    d = {}
    for i in range(len(j[0])):
        var_name = j[0][i]
        if isinstance(j[1][i], int):
            val = j[1][i]
        else:
            val = torch.tensor(j[1][i])
        d[var_name] = val
    return ([d[k] for k in varnames])


def main(args):
    advi = ADVIMaster(model)
    advi.add(ADVIDiagonalNormal(poutine.block(model, hide=["mixture"]))),
    advi.add(ADVIDiscreteParallel(poutine.block(model, expose=["mixture"])))

    adam = optim.Adam({'lr': 1e-3})
    svi = SVI(advi.model, advi.guide, adam, loss="ELBO")
    for i in range(100):
        loss = svi.step(*args)
        print('loss=', loss)
        if i % 5 == 0:
            d = advi.median()
#             print({k: d[k] for k in ["mu", "theta", "sigma"]})


if __name__ == "__main__":
    varnames = ["K", "alpha0", "y"]
    args = get_data("data/training.data.json", varnames)
    main(args)
