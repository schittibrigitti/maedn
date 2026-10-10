from scipy.optimize import curve_fit
from numpy import sqrt, divide, tanh

#global variables
P = 8	# no of players
D_0 = 10	# steps between players
F = 4			# no of figures per player
W = 1			# no of dices
A = 6			# no of eyes per dice

D = P*D_0
S = A*W/2 * A / (A-1)

n = 0.
t = 0.
t_end = 100000*P

dt = 1 # step width 

time = []
dens = []

def func(x, rho_0, t_0):
	return rho_0 * tanh(divide( x , t_0) )

def p_S(n_inp):
	p_S0 = (A**3 - (A-1)**3)/(A**3)
	p_S1 = 1/A*(1.-n_inp/(D*P))
	p_n = ((P-1)/P)**n_inp
	
	return p_S0 * p_n + p_S1 * (1 - p_n) 

def p_K(n_inp):
	return 1.-(1.-1./(A-1)*(P-1)/P * n/(D-n_inp/P)) ** (A*n_inp/P)


while t <= t_end:
	dn = W*p_S(n) - W*p_K(n)

	n = n + dn
	time.append(t)
	dens.append(n/D)

	t = t + dt

t_0 = P/W*sqrt(A*D_0)
r_0 = 1./sqrt(A*D_0)

fittedParameters, pcov = curve_fit(func, time, dens)

d_t0 = t_0/ fittedParameters[1]*dt -1
d_r0 = r_0/ fittedParameters[0] -1
d_PK = D_0*r_0**2 / p_K(fittedParameters[0]*D) -1

print("  parameters: P = %d D0 = %d, F = %d, W = %d, A = %d, s = %3.1f, t_ref = %3.1f Z/ %3.1f R" %(P,D_0, F, W, A, S, D/S*P, D/S))
print("   simulated: rho_0 = %3.3f, n_0 = %3.1f, t_0 = %3.1f Z / %3.1f R, p_K0 = %3.1f %%" % (fittedParameters[0],fittedParameters[0]*D/P,fittedParameters[1]/dt, fittedParameters[1]/P/dt, p_K(fittedParameters[0]*D)*100) )
print("approximated: rho_0 = %3.3f, n_0 = %3.1f, t_0 = %3.1f Z / %3.1f R, p_K0 = %3.1f %%" % (r_0,r_0*D/P,t_0, t_0/P, D_0*r_0**2*100) )
print("       error: %+3.3f %%, %+3.3f %%, %+3.3f %%" % (d_r0 * 100,d_t0 * 100, d_PK*100) )






