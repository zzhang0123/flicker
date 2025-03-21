import numpy as np
from linear_solver import cg, cg_mpi
from scipy.linalg import sqrtm, solve
from linear_sampler import iterative_gls, iterative_gls_mpi_list, sample_p, sample_p_old, sample_p_v2
import mpiutil


def Tsys_coeff_sampler(data, 
                       gain, 
                       Tsys_proj, 
                       Ncov, 
                       n_samples=1,
                       mu=0.0,
                       tol=1e-13,
                       prior_cov_inv=None, 
                       prior_mean=None, 
                       solver=cg):

    d_vec = data/gain
    Ncov_inv = np.linalg.inv(Ncov)
    p_GLS, sigma_inv = iterative_gls(d_vec, Tsys_proj, Ncov_inv, mu=mu, tol=tol)
    return sample_p_old(d_vec, Tsys_proj, sigma_inv, num_samples=n_samples,  mu=mu, prior_cov_inv=prior_cov_inv, prior_mean=prior_mean, solver=solver)

def Tsky_coeff_sampler_multi_TODs(local_data_list,
                                  local_gain_list,
                                  local_Tsys_proj_list,
                                  local_Ncov_list,
                                  local_mu_list=0.0,
                                  tol=1e-13,
                                  prior_cov_inv=None,
                                  prior_mean=None,
                                  solver=cg):
    d_vec_list = [local_data_list[i]/local_gain_list[i] for i in range(len(local_data_list))]
    Ncov_inv_list = [np.linalg.inv(Ncov) for Ncov in local_Ncov_list]

    p_GLS, A, b, Asqrt =  iterative_gls_mpi_list(d_vec_list, local_Tsys_proj_list, Ncov_inv_list, local_mu_list, tol=tol)
    if mpiutil.rank0:
        p_sample = sample_p_v2(A, b, Asqrt, prior_cov_inv=prior_cov_inv, prior_mean=prior_mean, solver=solver)
    # broadcast p_sample to all ranks
    p_sample = mpiutil.comm.bcast(p_sample, root=0)
    return p_sample

def Tsys_model(operator_list, params_vec_list):
    '''
    This function calculates the system temperature.

    Parameters:
    ----------
    operator_list : list of ndarray
        List of projection matrices. For example, [beam_proj, rec_proj, ndiode_proj].
    params_vec_list : list of ndarray
        List of parameter vectors. For example, [true_Tsky, rec_params, T_ndiode].

    Returns:
    -------
    Tsys : ndarray
        System temperature.
    '''
    assert len(operator_list) == len(params_vec_list), "Operator list and params list must have the same length.."
    n_components = len(operator_list)
    n_data = operator_list[0].shape[0]
    Tsys = np.zeros(n_data)

    for i in range(n_components):
        # if params_vec_list[i] is a scalar:
        if len(operator_list[i].shape) == 1:
            Tsys += operator_list[i] * params_vec_list[i]
        else:
            Tsys += operator_list[i] @ params_vec_list[i]

    return Tsys

def overall_operator(operator_list):
    '''
    This function calculates the overall operator.
    Parameters:
    ----------
    operator_list : list of ndarray
        List of projection matrices. For example, [beam_proj, rec_proj, ndiode_proj].

    Returns:
    -------
    overall_operator : ndarray
        Overall operator.
    '''
    aux_list = []
    for proj in operator_list:
        assert proj.shape[0] == operator_list[0].shape[0], "All projection matrices must have the same length.."
        if len(proj.shape) == 1:
            proj = proj.reshape(-1, 1)
        aux_list.append(proj)
    return np.hstack(aux_list)


        
    
