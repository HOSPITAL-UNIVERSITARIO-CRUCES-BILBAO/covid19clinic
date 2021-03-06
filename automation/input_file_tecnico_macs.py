# This script aims to update and customize the protocol for each sample
# run. Set the number of samples, date, register technician name and create
# the directories to run
from datetime import datetime
import os
import os.path
import pandas as pd
import string
import math
import time
homedir = os.path.expanduser("~")
main_path = '/Volumes/opentrons/'
code_path = main_path + 'code/covid19clinic/automation/'
KF_path = code_path + 'KF_config/'
HC_path = code_path + 'HC_config/'
excel = main_path + 'barcode_template/muestras.xlsx'

# Volumes for KF pathogen stations
security_volume_mmix = 50
security_volume_beads = 800
mmix_volume = 20
beads_volume = 10
isoprop_volume = 250

# Function to distinguish between HC and KF protocols
def select_protocol_type(p1, p2):
    ff=False
    while ff==False:
        protocol=input('Introducir protocolo: \nCustom protocol (HC) o Kingfisher (KF) \nProtocolo: ')
        if protocol=='KF':
            pr=protocol
            p=p1
            ff=True
        elif protocol=='HC':
            pr=protocol
            p=p2
            ff=True
        else:
            print('Please, try again')
    return pr,p

def rep_data(n, name, f, d, run_name):
    d=d.replace('$num_samples', str(n))
    d=d.replace('$technician', '\'' + str(name) + '\'')
    d=d.replace('$date', '\'' + str(f) + '\'')
    d=d.replace('$run_id','\'' + str(run_name) + '\'')
    return d

###############################################################################
def main():

    # Read the excel file from the run and obtain the dictionary of samples
    # muestras.xlsx
    df = pd.read_excel (excel,
     sheet_name='Deepwell layout', header = None, index_col = 0)
    df = df.iloc[1:]
    df_dict = df.to_dict('index')
    merged_dict={}
    for key in df_dict:
        for key2 in df_dict[key]:
            merged_dict[str(key)+format(key2)]=df_dict[key][key2]

    # count number of declared elements in Dictionary
    num_samples_control = 0
    for elem in merged_dict.values():
        if elem != 0:
            num_samples_control += 1

    # Get sample data from user
    control = False
    while control==False:
        num_samples = int(input('Número de muestras a procesar (incluidos PC + NC): '))
        if (num_samples>0 and num_samples<=96):
            control=True
        else:
            print('Número de muestras debe ser un número entre 1 y 96')
    print('El número de muestras registradas en el excel es: '+str(num_samples_control))
    if num_samples_control!=num_samples:
        print('Error: El número de muestras entre excel y reportado no coincide')
        exit()
    else:
        print('El número de muestras coincide')

    # Get technician name
    control = False
    while control==False:
        tec_name = (input('Nombre del técnico (usuario HCP): '))
        if isinstance(tec_name, str):
            control=True
        else:
            print('Introduce tu usuario HCP, por favor')

    # Get run session ID
    control=False
    while control==False:
        id = int(input('ID run: '))
        if isinstance(id,int):
            control=True
        else:
            print('Por favor, assigna un ID numérico para éste RUN')

    # Get date
    fecha = datetime.now()
    t_registro = fecha.strftime("%m/%d/%Y, %H:%M:%S")
    dia_registro = fecha.strftime("%Y_%m_%d")

    # select the type of protocol to be run
    [protocol,protocol_path]=select_protocol_type(KF_path, HC_path)
    #determine output path
    run_name = str(dia_registro)+'_OT'+str(id)+'_'+protocol
    final_path=os.path.join(main_path+'RUNS/',run_name)

    # create folder in case it doesn't already exist and copy excel registry file there
    if not os.path.isdir(final_path):
        os.mkdir(final_path)
        os.mkdir(final_path+'/scripts')
        os.mkdir(final_path+'/results')
        os.mkdir(final_path+'/logs')
        os.system('cp ' + excel +' '+ final_path+'/OT'+str(id)+'_samples.xlsx')

    if protocol=='KF':
        file_name = 'qpcr_template_OT'+str(id)+'_'+protocol+'.txt'
        os.system('python3 '+code_path+'thermoqpcr_generate_template.py "' + final_path + '/'+ file_name+'"')
    for file in os.listdir(protocol_path): # look for all protocols in folder
        if file.endswith('.py') and 'rmarkdown' not in file:
            fin = open(protocol_path+file, "rt") # open file and copy protocol
            data = fin.read()
            fin.close()
            final_protocol=rep_data(num_samples, tec_name, t_registro, data, run_name) #replace data
            position=file.find('_',12) # find _ position after the name and get value
            filename=str(dia_registro)+'_'+file[:position]+'_OT'+str(id)+'.py' # assign a filename date + station name + id
            for i in range(0,5): #Try up to 5 times with 1 sec delay
                while True:
                    try:
                        fout = open(os.path.join(final_path+'/scripts/',filename), "wt")
                        fout.write(final_protocol)
                        fout.close()
                    except SomeSpecificException:
                        time.sleep(1)
                        continue
                    break

        if file.endswith('.Rmd'):
            fin = open(protocol_path+file, "rt") # open file and copy protocol
            data = fin.read()
            fin.close()
            final_protocol=data.replace('$THERUN', str(run_name))
            filename=str(dia_registro)+'_OT'+str(id)+'.Rmd' # assign a filename date + station name + id
            fout = open(os.path.join(final_path+'/scripts/',filename), "wt")
            fout.write(final_protocol)
            fout.close()

    if protocol=='KF':
        #Calculate needed volumes and wells in stations B and C
        bead_vol = beads_volume * 8 * math.ceil(num_samples/8) * 1.1
        isoprop_vol = isoprop_volume * 8 * math.ceil(num_samples/8) * 1.1
        num_wells = math.ceil(num_samples / 32) #Number of wells needed

        #Add security volume according to proportion
        bead_vol = bead_vol + (security_volume_beads/(beads_volume + isoprop_volume)) * beads_volume * num_wells #Add security volume in each well
        isoprop_vol = isoprop_vol + (security_volume_beads/(beads_volume + isoprop_volume)) * isoprop_volume * num_wells #Add security volume in each well
        total_bead = bead_vol + isoprop_vol

        mmix_vol = (num_samples * 1.1 * mmix_volume)
        num_wells_mmix = math.ceil(mmix_vol/2000) #Number of wells needed
        mmix_vol = mmix_vol + (security_volume_mmix) * num_wells_mmix #Add security volume in each well
        reac1_vol = mmix_vol / 20 * 6.25
        reac2_vol = mmix_vol / 20 * 1.25
        nfree_vol = mmix_vol / 20 * 12.5

        #Print the information to a txt file
        f = open(final_path + '/OT' + str(id) + "volumes.txt", "wt")
        print('######### Station B ##########', file=f)
        print('Volumen y localización de beads para',num_samples, file=f)
        print('##############################', file=f)
        print('Es necesario un volumen de beads total de',format(round(total_bead)),' \u03BCl', file=f)
        print('La proporción de reactivos es:\n', round(bead_vol),'\u03BCl de beads \n',round(isoprop_vol), '\u03BCl de isopropanol\n', file=f)
        print('A dividir en',format(num_wells),'pocillos', file=f)
        print('Volumen por pocillo:',format(round(total_bead/num_wells)),'\u03BCl', file=f)
        print('',file=f)
        print('######### Station C ##########', file=f)
        print('Volumen y número tubos de MMIX para',num_samples, file=f)
        print('###############################', file=f)
        print('Serán necesarios',format(round(mmix_vol)),'\u03BCl', file=f)
        print('La proporción de reactivos es:\n', round(reac1_vol),'\u03BCl de 1-Step Multiplex Master Mix (No ROX, 4X)\n',round(reac2_vol), '\u03BCl de COVID-19 Assay Multiplex \n', round(nfree_vol),'\u03BCl de Nuclease-free water\n',file=f)
        print('A dividir en',format(num_wells_mmix),'pocillos', file=f)
        print('Volumen por pocillo:',format(round(mmix_vol/num_wells_mmix)),'\u03BCl', file=f)
        f.close()
        print('Revisa los volúmenes y pocillos necesarios en el archivo OT' + str(id) + 'volumes.txt dentro de la carpeta '+run_name)
        f2 = open(main_path + 'summary/run_history.txt','a')
        print(run_name, num_samples, tec_name, t_registro, file=f2)
        f2.close()
if __name__ == '__main__':
    main()
    print('Success!')
