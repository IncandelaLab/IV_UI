import matplotlib.pyplot as plt
import scipy.optimize    as opt

import numpy
import math
import time
import os



def proc_suffix(suffix):
	if suffix in DS_ALIASES.keys():
		suffix = DS_ALIASES[suffix]
	if suffix.startswith('data_'):
		return suffix[5:]
	return suffix

PATH = os.getcwd()

RAW_DATA_DIR = 'data'
RAW_DATA_FMT = 'data_{}.txt'

def load_raw_data(suffix,mult_current=None):
	suffix=proc_suffix(suffix)
	data = numpy.loadtxt(os.sep.join([PATH,RAW_DATA_DIR,RAW_DATA_FMT.format(suffix)]))
	if not (mult_current is None):
		data[...,2]*=mult_current
	return data

BIN_DIR = os.sep.join(['bins','{}'])
BIN_A_FMT = 'a_{}v.npy'
BIN_D_FMT = 'd_{}v.npy'
BIN_F_FMT = 'f_{}v.npy'
BIN_L_FMT = 'l_{}v.npy'
BIN_FMT = {'a':BIN_A_FMT,'d':BIN_D_FMT,'f':BIN_F_FMT,'l':BIN_L_FMT}

BIN_PLOT_DIR = os.sep.join([BIN_DIR,'plots'])
BIN_PLOT_FMT = '{}v.png'




###################
##  IV plotting  ##
###################

def plot_iv_all(suffix,moduleID=None):
	data = load_raw_data(suffix)
	plt.plot(data[...,1],data[...,2]*1e6,'r.')
	plt.xlabel("bias voltage (volts)")
	plt.ylabel("current (microamps)")
	if not (moduleID is None):
		plt.suptitle("Module {} IV curve\nup to {} volts".format(moduleID,data[...,1].max()))
	plt.show()







############
##  bins  ##
############

def save_bins(suffix,save_fl=False):
	suffix=proc_suffix(suffix)
	f,a,d,l = make_bins(load_raw_data(suffix))
	av_done = []
	dv_done = []

	# make bin folder if it doesn't exist yet
	if not os.path.exists(os.sep.join([PATH,BIN_DIR.format(suffix)])):
		os.mkdir(os.sep.join([PATH,BIN_DIR.format(suffix)]))

	for bin_ in a:
		v = int(bin_[0,1])
		if v in av_done:
			print("Warning: more than one bin with voltage {} in ascending bin list. All but the first are ignored.".format(v))
			continue
		av_done.append(v)
		numpy.save(os.sep.join([PATH,BIN_DIR.format(suffix),BIN_A_FMT.format(v)]),bin_)

	for bin_ in d:
		v = int(bin_[0,1])
		if v in dv_done:
			print("Warning: more than one bin with voltage {} in descending bin list. All but the first are ignored.".format(v))
			continue
		dv_done.append(v)
		numpy.save(os.sep.join([PATH,BIN_DIR.format(suffix),BIN_D_FMT.format(v)]),bin_)

	if save_fl:
		numpy.save(os.sep.join([PATH,BIN_DIR.format(suffix),BIN_F_FMT.format(int(f[0,1]))]),f)
		numpy.save(os.sep.join([PATH,BIN_DIR.format(suffix),BIN_L_FMT.format(int(f[0,1]))]),l)

def make_bins(raw_data,discard_first_point_per_bin=True):
	asc_bins  = []
	desc_bins = []

	first_bin    = None
	last_bin     = None
	this_bin     = []
	this_voltage = raw_data[0,1]
	this_bin_asc = None
	for data_point in raw_data:
		if data_point[1] == this_voltage:
			this_bin.append(data_point)
		else:
			if first_bin is None:
				first_bin = this_bin
			else:
				if len(this_bin) == 1:
					print("Warning: found bin of length 1. Bins of length 1 are ignored.")
				elif this_bin_asc:
					asc_bins.append(this_bin)
				elif not this_bin_asc:
					desc_bins.append(this_bin)

			if data_point[1] > this_voltage:
				this_bin_asc = True
			else:
				this_bin_asc = False

			this_voltage = data_point[1]
			this_bin     = [data_point]
	last_bin = this_bin
	if discard_first_point_per_bin:
		return numpy.array(first_bin)[1:],[numpy.array(_)[1:] for _ in asc_bins],[numpy.array(_)[1:] for _ in desc_bins],numpy.array(last_bin)[1:]
	else:
		return numpy.array(first_bin),[numpy.array(_) for _ in asc_bins],[numpy.array(_) for _ in desc_bins],numpy.array(last_bin)

def load_bin(suffix,v=0,category='a',normt=True,mult_current=1e6):
	suffix=proc_suffix(suffix)
	bin_ = numpy.load(os.sep.join([PATH,BIN_DIR.format(suffix),BIN_FMT[category].format(v)]))
	if not (mult_current is None):
		bin_[...,2]*=mult_current
	if normt:
		bin_[...,0]-=bin_[0,0]
	return bin_


#############
## fitting ##
#############

linear_fn      = lambda x,m,b:x*m + b
exponential_fn = lambda x,a,b,c:numpy.exp(-x*b)*a + c

def is_ordered(j,k,l):
	if j>k>l:return -1
	if j<k<l:return 1
	return 0

def third_markers(n):
	k = n//3
	r = n%3

	if r == 0:
		return k, k*2
	if r == 1:
		return k, k*2 + 1
	if r == 2:
		return k+1, 2*k + 1

def split_thirds(array):
	m1,m2 = third_markers(array.shape[0])
	return array[:m1],array[m1:m2],array[m2:]

def fit_exp_const_dx(X1,Y1,X2,Y2,X3,Y3,flacc=1e-6,spacing_override=True):

	if not spacing_override:
		if not fleq(X2-X1,X3-X2,flacc):
			print(X2-X1,X3-X2)
			raise ValueError("Not constant dx")

	if not is_ordered(Y1,Y2,Y3):
		raise ValueError("Y values not ordered")

	dX = (X3-X1)/2.0
	B = math.log((Y1-Y2)/(Y2-Y3))/dX
	A = (Y1-Y2)/(math.exp(-B*X1)-math.exp(-B*X2))
	C = Y1 - A * math.exp(-B*X1)

	return A,B,C

def do_exponential_fit(xdata,ydata):
	data = numpy.stack([xdata,ydata],-1)
	t1,t2,t3=split_thirds(data)
	m1=t1.mean(0)
	m2=t2.mean(0)
	m3=t3.mean(0)
	A,B,C=fit_exp_const_dx(*m1,*m2,*m3,spacing_override=True)
	if B<0:
		raise ValueError("Diverging exponential found (B<0)")
	popt,pcov = opt.curve_fit(exponential_fn, data[...,0], data[...,1], p0=[A,B,C])
	return popt,numpy.array([A,B,C]),numpy.stack([m1,m2,m3],0)


def do_linear_fit(xdata,ydata):
	n = len(xdata)
	if n != len(ydata):
		raise ValueError("Length of xdata ({}) not equal to length of ydata ({})".format(n,len(ydata)))
	if n < 2:
		raise ValueError("Must have at least 2 data points, found {}".format(n))
	x1 = xdata[:n//2].mean() 
	y1 = ydata[:n//2].mean()
	x2 = xdata[n//2:].mean()
	y2 = ydata[n//2:].mean()
	m_guess = (y1-y2)/(x1-x2)
	b_guess = y1 - m_guess*x1

	popt,pcov = opt.curve_fit(linear_fn,xdata,ydata,[m_guess,b_guess])
	return popt


def do_bin_linear_fit(bin_):
	return do_linear_fit(bin_[...,0],bin_[...,2])

def get_time_interval(bin_,tstart,tstop):
	return numpy.searchsorted(bin_[...,0],[tstart,tstop])

def do_timed_linear_fit(bin_,tstart,tstop):
	istart,istop = get_time_interval(bin_,tstart,tstop)
	return do_bin_linear_fit(bin_[istart:istop,...]),istop == bin_.shape[0]


##########################
##  plotting functions  ##
##########################

def plot_bin(bin_,save=False,suffix=''):
	suffix=proc_suffix(suffix)
	plt.plot(bin_[...,0],bin_[...,2],'r.')#,label='{}v'.format(int(bin_[0,1])))
	plt.xlabel('time (seconds) since stepping to {}v'.format(int(bin_[0,1])))
	plt.ylabel('current (microamps)')
	plt.suptitle('{}v'.format(int(bin_[0,1])))
	if save:
		fdir  = os.sep.join([PATH,BIN_PLOT_DIR.format(suffix)])
		fname = BIN_PLOT_FMT.format(int(bin_[0,1]))
		if not (os.path.exists(fdir)):
			os.mkdir(fdir)
		#plt.legend()
		plt.savefig(os.sep.join([fdir,fname]),dpi=128)
		plt.clf()
	else:
		plt.show()

def plot_dataset(suffix,suptitle=None,show=True,color='r',x_index=1):
	data = load_raw_data(suffix,mult_current=1e6)
	plt.plot(data[...,x_index],data[...,2],'{}.'.format(color))
	plt.xlabel("bias voltage (volts)")
	plt.ylabel("current (microamps)")
	if not (suptitle is None):
		plt.suptitle(suptitle)
	#plt.axhline(y=0.1,label='0.1 microamps')
	#plt.legend()
	if show:plt.show()

def plot_asc_desc(suffix,suptitle=None,descriptor="",show=True,asc_color='r',desc_color='b',max_points_per_bin=None,plot_means=False,plot_erb=False,skip=None):
	voltages = range(5,1090,5)
	first = [1,1]
	for v in voltages:

		if not (skip == 'a'):
			try:
				bin_ = load_bin(suffix,v)
				if not (max_points_per_bin is None):
					bin_ = bin_[:max_points_per_bin,:]

				rms = bin_.std(0)

				if plot_means:
					bin_ = bin_.mean(0)

				if first[0]:
					if plot_erb:
						plt.errorbar(bin_[...,1],bin_[...,2],yerr=rms[...,2],fmt='{}.'.format(asc_color),label='{} ascending voltage'.format(descriptor))
					else:
						plt.plot(bin_[...,1],bin_[...,2],'{}.'.format(asc_color),label='{} ascending voltage'.format(descriptor))
					first[0]=0
				else:
					if plot_erb:
						plt.errorbar(bin_[...,1],bin_[...,2],yerr=rms[...,2],fmt='{}.'.format(asc_color))
					else:
						plt.plot(bin_[...,1],bin_[...,2],'{}.'.format(asc_color))
			except:
				pass

		if not (skip == 'd'):
			try:
				bin_ = load_bin(suffix,v,category='d')
				if not (max_points_per_bin is None):
					bin_ = bin_[:max_points_per_bin,:]

				rms = bin_.std(0)

				if plot_means:
					bin_ = bin_.mean(0)

				if first[1]:
					if plot_erb:
						plt.errorbar(bin_[...,1],bin_[...,2],yerr=rms[...,2],fmt='{}.'.format(desc_color),label='{} descending voltage'.format(descriptor))
					else:
						plt.plot(bin_[...,1],bin_[...,2],'{}.'.format(desc_color),label='{} descending voltage'.format(descriptor))
					first[1]=0
				else:
					if plot_erb:
						plt.errorbar(bin_[...,1],bin_[...,2],yerr=rms[...,2],fmt='{}.'.format(desc_color))
					else:
						plt.plot(bin_[...,1],bin_[...,2],'{}.'.format(desc_color))
			except:
				pass

	plt.xlabel("bias voltage (volts)")
	plt.ylabel("current (microamps)")
	if suptitle:
		plt.suptitle(suptitle)
	plt.legend(loc = 2),
	if show:
		plt.show()

def plot_exponential_fit(bin_):
	popt,_,_ = do_exponential_fit(bin_[...,0],bin_[...,2])
	fit = exponential_fn(bin_[...,0],*popt)
	plt.plot(bin_[...,0],bin_[...,2],'r.',label='raw data')
	plt.plot(bin_[...,0],fit,'k--',label='exponential fit')
	plt.xlabel('time since start of bin (seconds)')
	plt.ylabel('current (microamps)')
	plt.suptitle("exponential fit of I(t) at {}v\ntau = {} seconds\npredicted settled current = {} microamps".format(bin_[0,1],'%.3E'%popt[1]**-1,'%.3E'%popt[2]))
	plt.show()

def make_m_of_tstop_plot(datasets,v,tstart,tstop_initial,tstop_final,tstop_steps):
	bins     = [load_bin(_,v) for _ in datasets]
	finished = [False for _ in bins]
	ms       = [[] for _ in bins]
	bs       = [[] for _ in bins]

	tstops = numpy.linspace(tstop_initial,tstop_final,tstop_steps)
	for tstop in tstops:

		for i,bin_ in enumerate(bins):
			popt,maxed = do_timed_linear_fit(bin_,tstart,tstop)
			#istart,istop = get_time_interval(bin_,tstart,tstop)
			#maxed = (istop == bin_.shape[0])
			if maxed:
				if finished[i]:
					continue
				else:
					finished[i]=True
			#ms[i].append(bin_[istart:istop,2].mean())
			ms[i].append(popt[0])
			bs[i].append(popt[1])

	for i,bin_ in enumerate(bins):
		plt.plot(tstops[:len(ms[i])],ms[i],'.',label=datasets[i])

	plt.xlabel('tstop (seconds)')
	plt.ylabel('m (slope of linear fit)')

	#plt.axhline(0,color='k',label='m = 0')
	#plt.axhline(0.1,color='k',label='m = 0.1')
	#plt.axhline(-1e-5,color='m',label='m = 1e-5')
	#plt.axvline(120,color='c',label='120 seconds')

	plt.legend()
	plt.show()

def make_lv_fit_plot(dataset,tstart,tstop):
	vs     = [5,10,15,20]
	colors = 'rgbk'
	for i,v in enumerate(vs):
		bin_ = load_bin(dataset,v)
		popt = do_timed_linear_fit(bin_,tstart,tstop)
		fit  = linear_fn(bin_[...,0],*popt)
		plt.plot(bin_[...,0],bin_[...,2],colors[i]+'.',label='{}v, m={}'.format(v,'%.3E'%popt[0]))
		plt.plot(bin_[...,0],fit,colors[i]+'--')

	plt.xlabel('time since start of bin (seconds)')
	plt.ylabel('current (microamps)')
	plt.suptitle('{}, linear fit from t = {} to {} seconds'.format(dataset,tstart,tstop))
	plt.legend()
	plt.show()

p = 'data_2018_9_7_9_58_52'
i = 'data_2018_9_7_11_29_45'

#plot_asc_desc(p,plot_means=True,asc_color='g',plot_erb=True,descriptor='PCB baseplate IV',skip='d',show=False)
#plot_asc_desc(i,plot_means=True,asc_color='r',plot_erb=True,descriptor='interposer IV',skip='d')

vs = range(10,1001,10)
vs_used = []
diffs = []
for v in vs:
	try:
		bp = load_bin(p,v)[...,2]
		bi = load_bin(i,v)[...,2]
		vs_used.append(v)
		diffs.append((bp.mean() - bi.mean())*1000)

	except:
		pass

plt.plot(vs_used,diffs,'r.')
plt.xlabel('bias voltage')
plt.ylabel('leakage current (nanoamps)')
plt.suptitle("PCB baseplate leakage current")
plt.show()

#save_bins('2018_7_26_17_20_42')
#plot_dataset('2018_7_13_10_29_45',show=False,color='b')
#plot_asc_desc('2018_7_13_10_29_45',show=False,asc_color='b',desc_color='c',max_points_per_bin=10,plot_means=True,plot_erb=True,descriptor='pre burn-in')
#plot_asc_desc('2018_7_26_17_20_42',show=True ,asc_color='r',desc_color='m',max_points_per_bin=10,plot_means=True,plot_erb=True,descriptor='post burn-in',suptitle='I/V before and after burn-in')




