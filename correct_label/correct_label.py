import json
import csv 
import numpy as np
import os
import matplotlib.pyplot as plt
import pandas as pd
import argparse
import logging

def read_args():
    parser = argparse.ArgumentParser()
                  
    parser.add_argument("--picks_file",
                        default="./picks.csv",
                        help="Picks file")
    
    parser.add_argument("--num_source",
                        default=None,
                        type=int,
                        help="Number of sources")
    
    parser.add_argument("--num_receiver",
                        default=None,
                        type=int,
                        help="Number of receiver")
                          
    parser.add_argument("--output_name",
                        default="label_time.csv",
                        help="Output label time name")
    
    parser.add_argument("--plot_figure",
                        action="store_true",
                        help="Plot figures")
    
    parser.add_argument("--p_pick_min",
                        default=None,
                        type=int,
                        help="Lower bound of P that helps to dectect anomalies")
    
    parser.add_argument("--p_pick_max",
                        default=None,
                        type=int,
                        help="Upper bound of P that helps to dectect anomalies")
    
    parser.add_argument("--s_pick_min",
                        default=None,
                        type=int,
                        help="Lower bound of S that helps to dectect anomalies")
    
    parser.add_argument("--s_pick_max",
                        default=None,
                        type=int,
                        help="Upper bound of S that helps to dectect anomalies")
    
    parser.add_argument("--std_coef",
                        default=None,
                        type=float,
                        help="A coefficient of standard deviation that is used to determine upper and lower bounds for detecting anomalies")
    
    parser.add_argument("--points_min_to_interpo",
                        default=10,
                        type=int,
                        help="Minumum of points considered to interpo")
                      
    args = parser.parse_args()
    return args

def pick_time(t,r_start,pick_min,pick_max):
    it = [json.loads(t[i]) for i in range(len(t))]
    r = []
    list_t = []
    for i in range(len(it)):
        try:
            if it[i][0]<pick_max and it[i][0]>pick_min: 
                list_t += [it[i][0]]
                r += [i+r_start]
        except:
            pass
    return r,list_t

def interpo_time_by_receiver(r,list_p,r_s,list_s):
    w=np.ones(len(r)) 
    a,b,c=np.polyfit(np.log(r),list_p,2,w=w)
    w_s=np.ones(len(r_s))
    m,n = np.polyfit(r_s,list_s,1,w=w_s)
    return (a,b,c),(m,n)

def interpo_and_detect_anomalies(r_p,list_p,r_s,list_s,flip,std_coef):
    if flip:
        (a,b,c),(m,n) = interpo_time_by_receiver(r_p,list_p[::-1],r_s,list_s)
        model_p = np.flip(np.copy(a*np.log(np.array(r_p))**2+b*np.log(np.array(r_p))+c))
    else:
        (a,b,c),(m,n) = interpo_time_by_receiver(r_p,list_p,r_s,list_s)
        model_p = np.copy(a*np.log(np.array(r_p))**2+b*np.log(np.array(r_p))+c)
    model_s = np.copy(m*np.array(r_s)+n)
    std_p = np.std(list_p)*std_coef
    std_s = np.std(list_s)*std_coef
    r_p_ = [r_p[i] for i in range(len(r_p)) if list_p[i]>model_p[i]-std_p and list_p[i]<model_p[i]+std_p]
    r_s_ = [r_s[i] for i in range(len(r_s)) if list_s[i]>model_s[i]-std_s and list_s[i]<model_s[i]+std_s]
    list_p_ = [list_p[i] for i in range(len(r_p)) if list_p[i]>model_p[i]-std_p and list_p[i]<model_p[i]+std_p]
    list_s_ = [list_s[i] for i in range(len(r_s)) if list_s[i]>model_s[i]-std_s and list_s[i]<model_s[i]+std_s]
    if flip:
        return interpo_time_by_receiver(r_p_,list_p_[::-1],r_s_,list_s_), ((a,b,c),(m,n)), (std_p,std_s)
    else:
        return interpo_time_by_receiver(r_p_,list_p_,r_s_,list_s_), ((a,b,c),(m,n)), (std_p,std_s)

def correct_label(args):
    
    label_file = args.picks_file
    num_source = args.num_source
    num_receiver = args.num_receiver
    outname = args.output_name
    plot = args.plot_figure
    points_min_to_interpo = args.points_min_to_interpo
    p_pick_min = args.p_pick_min
    s_pick_min = args.s_pick_min
    p_pick_max = args.p_pick_max
    s_pick_max = args.s_pick_max
    std_coef = args.std_coef
    
    if plot:
        if not os.path.exists('./figures'):
            os.makedirs('./figures')
            
    list_p_int = []
    list_s_int = []
    
    for source in range(1,num_source+1):
        i=source-1
        labeltime = pd.read_csv(label_file)
        tp = np.copy(labeltime['itp_pred'][num_receiver*i:num_receiver*i+num_receiver])
        ts = np.copy(labeltime['its_pred'][num_receiver*i:num_receiver*i+num_receiver])

        r_p_left,list_p_left = pick_time(tp[:i],1,p_pick_min,p_pick_max)
        r_s_left,list_s_left = pick_time(ts[:i],1,s_pick_min,s_pick_max)
        r_p_right,list_p_right = pick_time(tp[i:],source,p_pick_min,p_pick_max)
        r_s_right,list_s_right = pick_time(ts[i:],source,s_pick_min,s_pick_max)

        r_p = r_p_left + r_p_right
        r_s = r_s_left + r_s_right
        list_p = list_p_left + list_p_right
        list_s = list_s_left + list_s_right
        y_p = np.zeros(num_receiver)
        y_s = np.zeros(num_receiver)
        upper_P = np.zeros(num_receiver)
        upper_S = np.zeros(num_receiver)
        lower_P = np.zeros(num_receiver)
        lower_S = np.zeros(num_receiver)

        if source<points_min_to_interpo:
            ((a,b,c),(m,n)),((a0,b0,c0),(m0,n0)), (std_p,std_s) = interpo_and_detect_anomalies(r_p_right,list_p_right,r_s_right,list_s_right,False,std_coef)
            x = np.linspace(source,num_receiver,num_receiver-source+1)
            
            y_p[i:] = np.copy(a*np.log(x)**2+b*np.log(x)+c)
            y_s[i:] = np.copy(m*x+n)
            y_p[:i] = np.flip(np.copy(y_p[i:2*i]))
            y_s[:i] = np.flip(np.copy(y_s[i:2*i]))
            
            upper_P[i:] = np.copy(a0*np.log(x)**2+b0*np.log(x)+c0)+std_p
            upper_S[i:] = np.copy(m0*x+n0)+std_s
            upper_P[:i] = np.flip(np.copy(upper_P[i:2*i]))+std_p
            upper_S[:i] = np.flip(np.copy(upper_S[i:2*i]))+std_s
            lower_P[i:] = np.copy(a0*np.log(x)**2+b0*np.log(x)+c0)-std_p
            lower_S[i:] = np.copy(m0*x+n0)-std_s
            lower_P[:i] = np.flip(np.copy(lower_P[i:2*i]))-std_p
            lower_S[:i] = np.flip(np.copy(lower_S[i:2*i]))-std_s

        elif source<=num_receiver-points_min_to_interpo:
            ((a1,b1,c1),(m1,n1)),((a01,b01,c01),(m01,n01)), (std_p1,std_s1) = interpo_and_detect_anomalies(r_p_left,list_p_left,r_s_left,list_s_left,True,std_coef)
            ((a2,b2,c2),(m2,n2)),((a02,b02,c02),(m02,n02)), (std_p2,std_s2) = interpo_and_detect_anomalies(r_p_left[-1:]+r_p_right,list_p_left[-1:]+list_p_right,r_s_left[-1:]+r_s_right,list_s_left[-1:]+list_s_right,False,std_coef)
            x_right = np.linspace(source,num_receiver,num_receiver-source+1)
            x_left = np.linspace(1,source-1,source-1)

            y_p[i:] = np.copy(a2*np.log(x_right)**2+b2*np.log(x_right)+c2)
            y_p[:i] = np.flip(np.copy(a1*np.log(x_left)**2+b1*np.log(x_left)+c1))
            y_s[i:] = np.copy(m2*x_right+n2)
            y_s[:i] = np.copy(m1*x_left+n1)
            
            upper_P[i:] = np.copy(a02*np.log(x_right)**2+b02*np.log(x_right)+c02)+std_p2
            upper_P[:i] = np.flip(np.copy(a01*np.log(x_left)**2+b01*np.log(x_left)+c01))+std_p1
            upper_S[i:] = np.copy(m02*x_right+n02)+std_s2
            upper_S[:i] = np.copy(m01*x_left+n01)+std_s1
            lower_P[i:] = np.copy(a02*np.log(x_right)**2+b02*np.log(x_right)+c02)-std_p2
            lower_P[:i] = np.flip(np.copy(a01*np.log(x_left)**2+b01*np.log(x_left)+c01))-std_p1
            lower_S[i:] = np.copy(m02*x_right+n02)-std_s2
            lower_S[:i] = np.copy(m01*x_left+n01)-std_s1

        else:
            ((a,b,c),(m,n)),((a0,b0,c0),(m0,n0)), (std_p,std_s) = interpo_and_detect_anomalies(r_p_left,list_p_left,r_s_left,list_s_left,True,std_coef)
            x = np.linspace(1,source,source)

            y_p[:i+1] = np.flip(np.copy(a*np.log(x)**2+b*np.log(x)+c))
            y_s[:i+1] = np.copy(m*x+n)
            y_p[i+1:] = np.flip(np.copy(y_p[2*i-num_receiver+1:i]))
            y_s[i+1:] = np.flip(np.copy(y_s[2*i-num_receiver+1:i]))  
            
            lower_P[:i+1] = np.flip(np.copy(a0*np.log(x)**2+b0*np.log(x)+c0))-std_p
            lower_S[:i+1] = np.copy(m0*x+n0)-std_s
            lower_P[i+1:] = np.flip(np.copy(lower_P[2*i-num_receiver+1:i]))-std_p
            lower_S[i+1:] = np.flip(np.copy(lower_S[2*i-num_receiver+1:i]))-std_s
            
            upper_P[:i+1] = np.flip(np.copy(a0*np.log(x)**2+b0*np.log(x)+c0))+std_p
            upper_S[:i+1] = np.copy(m0*x+n0)+std_s
            upper_P[i+1:] = np.flip(np.copy(upper_P[2*i-num_receiver+1:i]))+std_p
            upper_S[i+1:] = np.flip(np.copy(upper_S[2*i-num_receiver+1:i]))+std_s

        if plot:
            x=np.linspace(1,num_receiver,num_receiver)
            plt.figure(i)
            plt.subplot(111)
            plt.xlabel('Receiver')
            plt.ylabel('Arrival time')
            plt.plot(r_p,list_p,'o',label='P picks')
            plt.plot(x,y_p,label='P corrected picks')
            plt.fill_between(x,lower_P,upper_P,label='Interpolation zone. std_coef={}'.format(std_coef),alpha=0.2)
            plt.legend()
            plt.savefig('./figures/Source {}_P'.format(source))
            plt.close(i)
            plt.figure(i)
            plt.subplot(111)
            plt.xlabel('Receiver')
            plt.ylabel('Arrival time')
            plt.plot(r_s,list_s,'o',label='S picks')
            plt.plot(x,y_s,label='S corrected picks')
            plt.fill_between(x,lower_S,upper_S,label='Interpolation zone. std_coef={}'.format(std_coef),alpha=0.2)
            plt.legend()
            plt.savefig('./figures/Source {}_S'.format(source))
            plt.close(i)

        p_int = [round(j) for j in y_p]
        s_int = [round(j) for j in y_s]
        list_p_int += p_int
        list_s_int += s_int
        
    if plot:
        logging.info('Figures stored in {}'.format('figures')) 
    dataframe = pd.DataFrame({'itp':list_p_int,'its':list_s_int})
    dataframe.to_csv(outname,index=False)
    logging.info('Label times are saved in {}'.format(outname))

def main(args):
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    correct_label(args)
    return

if __name__ == '__main__':
  args = read_args()
  main(args)