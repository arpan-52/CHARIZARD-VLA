# Standard Library Imports
import os
import sys
import re
import time
from datetime import datetime
import logging
import subprocess

# Third-Party Imports
import argparse
import configparser


# Function to configure a logger
def configure_logger(name, log_file, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create file handler which logs even debug messages
    fh = logging.FileHandler(log_file)
    fh.setLevel(level)
    
    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # Add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

def extract_log_file_path(pbs_file):
    """
    Extract the log file path from the PBS script.
    """
    log_path = None
    try:
        with open(pbs_file, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith("#PBS -o"):
                    # Extract the log path after the '-o' flag
                    parts = line.split()
                    if len(parts) > 1:
                        log_path = parts[2].strip()
                    break
    except Exception as e:
        print(f"Error reading {pbs_file}: {e}")
    return log_path


def wait_for_jobs_to_finish(job_ids, base_output_dir, logger, prefix):
    """
    Wait for all jobs to finish, check their log files, and clean up files.
    job_ids should be a list of job IDs.
    """
    all_successful = True
    failed_jobs = []

    while job_ids:
        time.sleep(60)  # Check every minute
        for job_id in job_ids[:]:
            try:
                qstat_command = f"qstat {job_id}"
                result = subprocess.run(qstat_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:  # If qstat fails, job is probably finished
                    job_ids.remove(job_id)

                    # Locate the PBS file for the job
                    pbs_file = f"{prefix}.pbs"
                    log_file_path = extract_log_file_path(pbs_file)

                    # Construct the log file path relative to base_output_dir
                    if log_file_path:
                        log_file = os.path.join(base_output_dir, os.path.basename(log_file_path))
                        print(log_file)
                    else:
                        log_file = os.path.join(base_output_dir, f"{prefix}.log")

                    if os.path.exists(log_file):
                        with open(log_file, 'r') as log:
                            log_content = log.read()
                            if "error" in log_content.lower():
                                logger.error(f"Job {job_id} failed. Check log file {log_file}.")
                                all_successful = False
                                failed_jobs.append(job_id)
                            else:
                                logger.info(f"Job {job_id} completed successfully.")
                    else:
                        logger.error(f"Log file for job {job_id} not found or invalid path.")
                        all_successful = False
                        failed_jobs.append(job_id)

            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to check job status for {job_id}: {e}")
                all_successful = False
                failed_jobs.append(job_id)

    return all_successful, failed_jobs


def cleanup_files(job_id, logger, prefix):
    """
    Delete .py and .pbs files for the given job ID.
    """
    try:
        # Construct file paths (absolute paths are better if working in different directories)
        python_file = os.path.join(os.getcwd(), f"{prefix}.py")
        pbs_file = os.path.join(os.getcwd(), f"{prefix}.pbs")

        # Log the full paths to help debug any issues
        logger.info(f"Attempting to delete files: {python_file}, {pbs_file}")

        if os.path.exists(python_file):
            os.remove(python_file)
            logger.info(f"Deleted {python_file}")
        else:
            logger.warning(f"{python_file} not found for deletion.")

        if os.path.exists(pbs_file):
            os.remove(pbs_file)
            logger.info(f"Deleted {pbs_file}")
        else:
            logger.warning(f"{pbs_file} not found for deletion.")
            
    except Exception as e:
        # Log more details if an exception occurs
        logger.error(f"Error during cleanup for job {job_id} with prefix {prefix}: {e}")



def check_jobs_status(job_ids, working_directory, logger, prefix):
    """
    Check the status of jobs in the provided list and handle cleanup.

    Args:
        job_ids (list): List of job IDs.
        working_directory (str): Path to the working directory.
        logger (logging.Logger): Logger instance.

    Returns:
        bool: True if all jobs are completed, False otherwise.
    """
    if not job_ids:
        logger.info("No jobs to check.")
        return True

    all_successful, failed_jobs = wait_for_jobs_to_finish(job_ids, working_directory, logger, prefix)

    if all_successful:
        logger.info("All jobs in the list have been completed.")
        # Perform cleanup for all job IDs
        for job_id in job_ids:
            cleanup_files(job_id, logger, prefix)
    else:
        logger.error(f"Some jobs failed. The following job IDs had issues: {', '.join(failed_jobs)}")

    return all_successful


def parse_config(config_file):
    """
    Read the configuration file and return the parameters.

    Args:
        config_file (str): Path to the configuration file.

    Returns:
        dict: Parsed configuration parameters.
    """
    config = configparser.ConfigParser()
    config.read(config_file)

    try:
        # Extract parameters from the config file
        params = {
            "working_dir": config['DEFAULT'].get('working_dir', '').strip(),
            "msname": config['DEFAULT'].get('msname', '').strip(),
            "pacal": config['DEFAULT'].get('pacal', '').strip(),
            "leakcal": config['DEFAULT'].get('leakcal', '').strip(),
            "ref_ant": config['DEFAULT'].get('ref_ant', '').strip(),
            "selfcal": config['DEFAULT'].getboolean('selfcal', False),
            "selfcal_ms": config['DEFAULT'].get('selfcal_ms', '').strip(),
            "solint": [
                interval.strip() for interval in config['DEFAULT'].get('solint', '').split(',')
                if interval.strip()
            ],
            "pcal": config['DEFAULT'].getint('pcal', 0),
            "apcal": config['DEFAULT'].getint('apcal', 0),
            "niter_s": config['DEFAULT'].getint('niter_s', 0),
            "chanaverage": config['DEFAULT'].getboolean('chanaverage', False),
            "chanbin": config['DEFAULT'].getint('chanbin', 0),
            "casa_dir": config['DEFAULT'].get('casa_dir', '').strip(),
            "vla_pipe_dir": config['DEFAULT'].get('vla_pipe_dir', '').strip(),
        }

        return params

    except configparser.Error as e:
        raise ValueError(f"Error parsing configuration file '{config_file}': {e}")



def initial_calibration(working_dir, ms_in, vla_pipe_dir, logger,prefix):
    """
    Create a PBS script for the given subband and submit it to the queue.
    This function also performs pre-calibration steps as part of the calibration process.
    """
    # Python script content for CASA commands
    python_script_content = f"""
__rethrow_casa_exceptions = True
context = h_init()
context.set_state('ProjectSummary', 'observatory', 'Karl G. Jansky Very Large Array')
context.set_state('ProjectSummary', 'telescope', 'EVLA')
try:
    hifv_importdata(vis='{ms_in}', createmms='automatic', asis='Receiver CalAtmosphere', ocorr_mode='co', nocopy=False, overwrite=False)
    hifv_hanning(pipelinemode="automatic")
    hifv_flagdata(tbuff=0.0, flagbackup=False, scan=True, fracspw=0.05, intents='*POINTING*,*FOCUS*,*ATMOSPHERE*,*SIDEBAND_RATIO*, *UNKNOWN*, *SYSTEM_CONFIGURATION*, *UNSPECIFIED#UNSPECIFIED*', clip=True, baseband=True, shadow=True, quack=True, edgespw=True, autocorr=True, hm_tbuff='1.5int', template=True, online=True)
    hifv_vlasetjy(pipelinemode="automatic")
    hifv_priorcals(pipelinemode="automatic")
    hifv_testBPdcals(weakbp=False, refantignore='ea01,ea02,ea03,ea04,ea05,ea06,ea07,ea08,ea09,ea11,ea12,ea13,ea14,ea15,ea16,ea17,ea18,ea19,ea20,ea21,ea22,ea23,ea24,ea26,ea28')
    hifv_checkflag(pipelinemode="automatic")
    hifv_semiFinalBPdcals(weakbp=False, refantignore='ea01,ea02,ea03,ea04,ea05,ea06,ea07,ea08,ea09,ea11,ea12,ea13,ea14,ea15,ea16,ea17,ea18,ea19,ea20,ea21,ea22,ea23,ea24,ea26,ea28')
    hifv_checkflag(checkflagmode='automatic')
    hifv_semiFinalBPdcals(weakbp=False, refantignore='ea01,ea02,ea03,ea04,ea05,ea06,ea07,ea08,ea09,ea11,ea12,ea13,ea14,ea15,ea16,ea17,ea18,ea19,ea20,ea21,ea22,ea23,ea24,ea26,ea28')
    hifv_solint(pipelinemode="automatic", refantignore='ea01,ea02,ea03,ea04,ea05,ea06,ea07,ea08,ea09,ea11,ea12,ea13,ea14,ea15,ea16,ea17,ea18,ea19,ea20,ea21,ea22,ea23,ea24,ea26,ea28')
    hifv_fluxboot(fitorder=-1, refantignore='ea01,ea02,ea03,ea04,ea05,ea06,ea07,ea08,ea09,ea11,ea12,ea13,ea14,ea15,ea16,ea17,ea18,ea19,ea20,ea21,ea22,ea23,ea24,ea26,ea28')
    hifv_finalcals(weakbp=False, refantignore='ea01,ea02,ea03,ea04,ea05,ea06,ea07,ea08,ea09,ea11,ea12,ea13,ea14,ea15,ea16,ea17,ea18,ea19,ea20,ea21,ea22,ea23,ea24,ea26,ea28')
    hifv_applycals(flagdetailedsum=True, gainmap=False, flagbackup=True, flagsum=True)
    hifv_targetflag(intents='*CALIBRATE*,*TARGET*')
    hifv_statwt(datacolumn='corrected')
finally:
    h_save()
"""

    # Create the Python script file
    python_script_file = f"{prefix}.py"
    with open(python_script_file, "w") as file:
        file.write(python_script_content)

    # Define working directory and PBS script content
    working_dir = os.getcwd()
    pbs_script_content = f"""#!/bin/bash
#PBS -N {prefix}
#PBS -l nodes=1:ppn=2
#PBS -l walltime=10:00:00
#PBS -j oe
#PBS -o {prefix}.log
#PBS -q workq

cd {working_dir}
source ~/.bashrc
micromamba activate 38data
{vla_pipe_dir}/bin/casa --pipeline --nogui -c {python_script_file}
"""

    # Create the PBS script file
    pbs_script_file = f"{prefix}.pbs"
    with open(pbs_script_file, "w") as file:
        file.write(pbs_script_content)

    # Submit the PBS script to the queue
    submit_command = f"qsub {pbs_script_file}"
    logger.info(f"Submitting PBS script to get calibration solutions: {submit_command}")
    try:
        result = subprocess.run(submit_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        job_id = result.stdout.decode().strip()  # Job ID is the output from qsub
        logger.info(f"PBS calibration script for {prefix} submitted successfully with job ID: {job_id}")
        return job_id, prefix
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to submit PBS script for {prefix}: {e}")
        return None, prefix

def find_latest_log(log_dir):
    """
    Find the most recently modified CASA log file in the specified directory.
    Args:
        log_dir (str): Directory to search for CASA log files.
    Returns:
        str: Path to the latest CASA log file.
    """
    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.startswith("casa") and f.endswith(".log")]
    if not log_files:
        raise FileNotFoundError("No CASA log files found in the specified directory.")
    latest_log = max(log_files, key=os.path.getmtime)
    return latest_log

def extract_setjy_params(log_file, source_name):
    """
    Extract `setjy` parameters for a given source from a CASA log file.
    Args:
        log_file (str): Path to the CASA log file.
        source_name (str): Name of the source to search for in the log file.
    Returns:
        str: CASA `setjy` command with the extracted parameters.
    """
    # Define the regex pattern to match the relevant source entry
    pattern = (
        rf"# Fitted spectrum for {source_name} with fitorder=2: "
        r"Flux density = ([\d.]+) \+/- [\d.e+-]+ \(freq=([\d.]+) GHz\) spidx: "
        r"a_1 \(spectral index\) =([\d.e+-]+) \+/- [\d.e+-]+ a_2=([\d.e+-]+) \+/- [\d.e+-]+"
    )
    
    # Open the log file and search for the entry
    with open(log_file, 'r') as f:
        log_content = f.read()
        
    match = re.search(pattern, log_content)
    
    if not match:
        raise ValueError(f"Source {source_name} not found in the log file.")
    
    # Extract parameters
    flux_density = float(match.group(1))
    freq_ghz = float(match.group(2))
    a_1 = float(match.group(3))
    a_2 = float(match.group(4))
    
    return flux_density, a_1, a_2, freq_ghz

def refine_calibration(working_dir, ms_in, casa_dir, logger, pacal, leakcal, prefix):
    """
    Create a PBS script to refine the calibrations and do a full-polar re-calibration.
    """
    # Define gaintable dynamically
    gaintable = [
        f"{ms_in}.hifv_priorcals.s5_2.gc.tbl",
        f"{ms_in}.hifv_priorcals.s5_3.opac.tbl",
        f"{ms_in}.hifv_priorcals.s5_4.rq.tbl",
        f"{ms_in}.hifv_priorcals.s5_6.ants.tbl",
        f"{ms_in}.hifv_finalcals.s13_2.finaldelay.tbl",
        f"{ms_in}.hifv_finalcals.s13_4.finalBPcal.tbl",
        f"{ms_in}.hifv_finalcals.s13_5.averagephasegain.tbl",
        f"{ms_in}.hifv_finalcals.s13_7.finalampgaincal.tbl",
        f"{ms_in}.hifv_finalcals.s13_8.finalphasegaincal.tbl"
    ]

    gainfield=['', '', '', '', '', '', '', '', '']
    interp = ['', '', '', '', '', 'linear,linearflag', '', '', '']

    # Placeholder for CASA script generation
    python_script_content = f"""
# CASA Python Script for Refining Calibration
gaintable = {gaintable}
gainfield = {gainfield}
interp = {interp}

applycal(
    vis='{ms_in}',
    antenna='*&*',
    gaintable=gaintable,
    gainfield=gainfield,
    interp=interp,
    spwmap=[[], [], [], [], [], [], [], [], []],  # No spw mapping
    calwt=[False, False, False, False, False, False, False, False, False],  # No weighting applied
    parang=False,  # No parallactic angle correction
    applymode='calflagstrict',  # Strict flagging mode
    flagbackup=False  # No additional flag backup
)


flagdata(vis='{ms_in}', mode='rflag', correlation='ABS_LL,RR', intent='*CALIBRATE*', datacolumn='corrected', ntime='scan', combinescans=False, extendflags=False, winsize=3, timedevscale=4.0, freqdevscale=4.0, action='apply', flagbackup=False, savepars=True)

flagdata(vis='{ms_in}', mode='rflag', correlation='ABS_LL,RR', intent='*TARGET*', datacolumn='corrected', ntime='scan', combinescans=False, extendflags=False, winsize=3, timedevscale=4.0, freqdevscale=4.0, action='apply', flagbackup=False, savepars=True)

statwt(vis='{ms_in}', minsamp=8, datacolumn='corrected', flagbackup=False)


# Setjy for Polarization Calibrator
setjy(
    vis='{ms_in}',
    field='{pacal['source']}',
    spw='',
    selectdata=False,
    scalebychan=True,
    standard="manual",
    fluxdensity=[{pacal['stokes_I']}, 0, 0, 0],
    spix={pacal['spectral_index']},
    reffreq="{pacal['reffreq']}",
    polindex={pacal['polarization_fraction']},
    polangle={pacal['polarization_angle']},
    usescratch=True,
    rotmeas=0,
    useephemdir=False,
    interpolation="nearest",
    usescratch=True,
    ismms=False,
)

# Setjy for Leakage Calibrator
setjy(
    vis='{ms_in}',
    field='{leakcal['source']}',
    spw='',
    selectdata=False,
    scalebychan=True,
    standard="manual",
    fluxdensity=[{leakcal['stokes_I']}, 0, 0, 0],
    spix={leakcal['spectral_index']},
    reffreq="{leakcal['reffreq']}",
    usescratch=True,
    polindex=[],
    polangle=[],
    rotmeas=0,
    useephemdir=False,
    interpolation="nearest",
    usescratch=True,
    ismms=False,
)


# Solve using Single Band Delay

kcross_sbd = "{pacal['source']}.cross_sbd"
gaincal(vis='{ms_in}',
    caltable=kcross_sbd,
    field="{pacal['source']}",
    spw='',
    refant='ea10',
    gaintype="KCROSS",
    solint="inf",
    combine="scan",
    calmode="ap",
    append=False,
    gaintable=gaintable,
    gainfield=gainfield,
    interp=interp,
    parang=True)

gaintable.append(kcross_sbd)
gainfield.append('')
interp.append('')


####### Df

dtab = '{leakcal['source']}.Df' 
polcal(vis='{ms_in}',
       caltable=dtab,
       field='{leakcal['source']}',
       spw='',
       refant='ea10',
       poltype='Df',
       solint='inf,2MHz',
       combine='scan',
       gaintable=gaintable,
       gainfield=gainfield,
       interp=interp,
       append=False)

gaintable.append(dtab)
gainfield.append('')
interp.append('')

# In CASA
xtab = "{pacal['source']}.Xf"
polcal(vis='{ms_in}',
       caltable=xtab,
       spw='',
       field='{pacal['source']}',
       solint='inf,2MHz',
       combine='scan',
       poltype='Xf',
       refant = 'ea10',
       gaintable=gaintable,
       gainfield=gainfield,
       append=False)

gaintable.append(xtab)
gainfield.append('')
interp.append('')

#experiment

applycal(vis='{ms_in}', 
	 antenna='*&*', 
	 gaintable = gaintable, 
	 gainfield=['', '', '', '', '', '', '', '', '','','',''], 
	 interp=['', '', '', '', '', 'linear,linearflag', '', '', '','','',''], 
	 spwmap=[[], [], [], [], [], [], [], [], [],[],[],[]], 
	 calwt=[False, False, False, False, False, False, False, False, False, False, False, False], 
	 parang=True, 
	 applymode='calflagstrict', 
	 flagbackup=False)
"""
    # Create the Python script file
    python_script_file = f"{prefix}.py"
    with open(python_script_file, "w") as file:
        file.write(python_script_content)

    # Define working directory and PBS script content
    working_dir = os.getcwd()
    pbs_script_content = f"""#!/bin/bash
#PBS -N {prefix}
#PBS -l nodes=1:ppn=4
#PBS -l walltime=10:00:00
#PBS -j oe
#PBS -o {prefix}.log
#PBS -q workq

cd {working_dir}
source ~/.bashrc
micromamba activate 38data
{casa_dir}/bin/casa --pipeline --nogui -c {python_script_file}
"""

    # Create the PBS script file
    pbs_script_file = f"{prefix}.pbs"
    with open(pbs_script_file, "w") as file:
        file.write(pbs_script_content)

    # Submit the PBS script to the queue
    submit_command = f"qsub {pbs_script_file}"
    logger.info(f"Submitting PBS script to refine calibration solutions: {submit_command}")
    try:
        result = subprocess.run(submit_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        job_id = result.stdout.decode().strip()  # Job ID is the output from qsub
        logger.info(f"PBS calibration script for {prefix} submitted successfully with job ID: {job_id}")
        return job_id, prefix
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to submit PBS script for {prefix}: {e}")
        return None, prefix
    

def call_wsclean(working_dir, msname,imagename,logger,niter,datacolumn):
    pbs_script_content = f"""#!/bin/bash
#PBS -N wsclean
#PBS -l nodes=1:ppn=1
#PBS -l walltime=10:00:00
#PBS -j oe
#PBS -o {imagename}.log
#PBS -q workq

cd {working_dir}
source ~/.bashrc
micromamba activate 38data
wsclean -name {imagename} -weight briggs 0.0 -super-weight 1.0 -weighting-rank-filter-size 16 -taper-gaussian 0 -size 100 100 -scale 0.6asec -channels-out 4 -wstack-grid-mode kb -wstack-kernel-size 7 -wstack-oversampling 63 -pol I -intervals-out 1 -data-column {datacolumn} -niter {niter} -auto-mask 5 -auto-threshold 0.05 -gain 0.1 -mgain 0.9 -join-channels -multiscale-scale-bias 0.6 -fit-spectral-pol 3 -fit-beam -elliptical-beam -padding 1.3 -parallel-deconvolution 8192 {msname}

"""

    pbs_script_file = f"{imagename}.pbs"
    with open(pbs_script_file, "w") as file:
        file.write(pbs_script_content)

    submit_command = f"qsub {pbs_script_file}"
    logger.info(f"Submitting PBS script for {imagename} to image first")
    try:
        result = subprocess.run(submit_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        job_id = result.stdout.decode().strip()  # Job ID is the output from qsub
        logger.info(f"PBS calibration script for {imagename} submitted successfully with job ID: {job_id}")
        return job_id, imagename
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to submit PBS script for {imagename}: {e}")
        return None, imagename

def calbrate_ap(working_dir,ms_in, ms_out, casa_dir, logger,ref_ant,sol_int,solname,calmode):
    """
    Create a PBS script for the given subband and submit it to the queue.
    """
    python_script_content = f"""ms_name = '{ms_in}'
gt = '{solname}.tbl'
bp = '{solname}.bp'
outputms = '{ms_out}'

gaincal(vis=ms_name, caltable=gt, field='', solint='{sol_int}', refant='{ref_ant}',
        spw='', minsnr=2.0, gaintype='G', parang=False, calmode='{calmode}')

bandpass(vis=ms_name, caltable=bp, field='', solint='inf', refant='{ref_ant}', minsnr=3.0, spw='',
         parang=False, gaintable=[gt], interp=[])

applycal(vis=ms_name, gaintable=[gt, bp], spw='', applymode='calflag', parang=False)

mstransform(vis = ms_name, outputvis=outputms , spw='', datacolumn='corrected')

"""

    python_script_file = f"{solname}.py"
    with open(python_script_file, "w") as file:
        file.write(python_script_content)

    working_dir = os.getcwd()
    pbs_script_content = f"""#!/bin/bash
#PBS -N {solname}
#PBS -l nodes=1:ppn=2
#PBS -l walltime=10:00:00
#PBS -j oe
#PBS -o {solname}.log
#PBS -q workq

cd {working_dir}
source ~/.bashrc
micromamba activate 38data
{casa_dir}/bin/casa --nogui -c {python_script_file}
"""

    pbs_script_file = f"{solname}.pbs"
    with open(pbs_script_file, "w") as file:
        file.write(pbs_script_content)

    submit_command = f"qsub {pbs_script_file}"
    logger.info(f"Submitting PBS script to get calibration solutions: {submit_command}")
    try:
        result = subprocess.run(submit_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        job_id = result.stdout.decode().strip()  # Job ID is the output from qsub
        logger.info(f"PBS calibration script for {solname} submitted successfully with job ID: {job_id}")
        return job_id, solname
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to submit PBS script for {solname}: {e}")
        return None, solname
    

def splitting_ms(ms_in, ms_out, casa_dir, logger, spw, chanaverage, chanbin, field, prefix):
    """
    Create a PBS script to split an MS.
    """
    # Conditional inclusion of the `chanbin` parameter
    chanbin_line = f", chanbin = {chanbin}" if chanaverage else ""

    python_script_content = f"""ms_name = '{ms_in}'
outputms = '{ms_out}'

mstransform(vis=ms_name, 
            outputvis=outputms, 
            spw='{spw}', 
            datacolumn='corrected', 
            chanaverage={chanaverage}{chanbin_line}, 
            field='{field}')
"""
    # Log the generated script content
    logger.info(f"Generated CASA script for splitting MS")

    python_script_file = f"{prefix}.py"
    with open(python_script_file, "w") as file:
        file.write(python_script_content)

    working_dir = os.getcwd()
    pbs_script_content = f"""#!/bin/bash
#PBS -N {prefix}
#PBS -l nodes=1:ppn=2
#PBS -l walltime=10:00:00
#PBS -j oe
#PBS -o {prefix}.log
#PBS -q workq

cd {working_dir}
source ~/.bashrc
micromamba activate 38data
{casa_dir}/bin/casa --nogui -c {python_script_file}
"""

    pbs_script_file = f"{prefix}.pbs"
    with open(pbs_script_file, "w") as file:
        file.write(pbs_script_content)

    submit_command = f"qsub {pbs_script_file}"
    logger.info(f"Submitting PBS script to get MS transform: {submit_command}")
    try:
        result = subprocess.run(submit_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        job_id = result.stdout.decode().strip()  # Job ID is the output from qsub
        logger.info(f"PBS calibration script for {prefix} submitted successfully with job ID: {job_id}")
        return job_id, prefix
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to submit PBS script for {prefix}: {e}")
        return None, prefix

def get_mode_and_index(i, pcal):
    """
    Determines the mode and index based on the given parameters.

    Parameters:
    i (int): Current iteration index.
    pcal (int): Number of p-calibration steps.
    apcal (int): Number of ap-calibration steps.

    Returns:
    tuple: A tuple containing the mode ('p' or 'ap') and the corresponding index (int).
    """
    if i < pcal:
        mode = 'p'
        j = i + 1 
    else:
        mode = 'ap'
        j = i - pcal + 1 
    return mode, j

def selfcal(msname,working_dir,solint,pcal, apcal, niter_s,logger,casa_dir,ref_ant ):
    """
    Perform self-calibration and imaging.

    Parameters:
    msname (str): Measurement set name.
    working_dir (str): Directory where processing is done.
    solint (list): List of solution intervals.
    pcal (int): Number of phase calibration steps.
    apcal (int): Number of amplitude-phase calibration steps.
    niter_s (int): Number of iterations scaling factor.
    logger (Logger): Logger for logging messages.
    """
    imagename = 'img' + '_initial' 
    niter = niter_s
    logger.info("Starting initial imaging with WSClean.")
    # job_id, prefix =  call_wsclean(working_dir, msname,imagename,logger,niter)
    job_id, prefix = call_wsclean(working_dir, msname,imagename,logger,niter,'DATA')

    # Create a list to track job IDs
    job_info = [job_id]
    logger.info(f"Initial job submitted with Job ID: {job_info}")
    
    # Wait for jobs to finish
    all_successful, failed_jobs = wait_for_jobs_to_finish(job_info, working_dir, logger, prefix)

    if all_successful:
        logger.info("Initial imaging completed successfully. Proceeding to clean up.")
        job_info = [job_id]                                  # Because wait_for_jobs remove all the jobs that are done.
        for job_id in job_info:
            logger.info(f"Cleaning up files for Job ID: {job_id} with prefix: {prefix}")
            cleanup_files(job_id, logger, prefix)
    else:
        logger.error(f"Initial imaging failed. The following Job IDs had issues: {', '.join(map(str, failed_jobs))}")
        sys.exit(1)


    logger.info("All initial jobs completed. Proceeding to self-calibration.")

    total = pcal + apcal
    if total != len(solint):
        logger.error("Mismatch between solint and the number of calibration times.")
        raise ValueError("Check solint and the number of calibration times.")
    logger.info("Validated solution intervals against calibration steps.")

    # Step 3: Perform self-calibration and imaging
    for i in range(len(solint)):
        logger.info(f"Starting self-calibration iteration {i + 1}/{len(solint)}.")

        # Determine mode (p or ap) and corresponding index
        mode, j = get_mode_and_index(i, pcal)
        solname = f'self_{mode}{j}'  # Name for calibration solution
        imagename = f'img_{mode}{j}'  # Name for output image
        sint = solint[i]  # Solution interval for current iteration

        # Set input and output measurement set names
        if i == 0:
            ms_in = msname  # Use original measurement set for the first iteration
            ms_out = solname + '.ms'
        else:
            prev_mode, k = get_mode_and_index(i - 1, pcal)
            ms_in = f'self_{prev_mode}{k}.ms'  # Previous iteration's output
            ms_out = solname + '.ms'

        logger.info(f"Calibration mode: {mode}, Index: {j}, MS In: {ms_in}, MS Out: {ms_out}")

        # Perform calibration
        job_id, prefix = calbrate_ap(working_dir, ms_in, ms_out, casa_dir, logger, ref_ant, sint, solname, mode)

        # Track calibration job
        job_info = [job_id]
        logger.info(f"Calibration job submitted with Job ID: {job_info}")

        # Wait for calibration jobs to finish
        all_successful, failed_jobs = wait_for_jobs_to_finish(job_info, working_dir, logger, prefix)

        if all_successful:
            logger.info("Calibration completed successfully. Proceeding to clean up.")
            job_info = [job_id]
            for job_id in job_info:
                logger.info(f"Cleaning up files for Job ID: {job_id} with prefix: {prefix}")
                cleanup_files(job_id, logger, prefix)
        else:
            logger.error(f"Calibration failed. The following Job IDs had issues: {', '.join(map(str, failed_jobs))}")
            sys.exit(1)

        logger.info(f"Self-calibration iteration {i + 1} completed. Proceeding to imaging.")

        # Imaging after calibration
        niter = niter_s * (i + 2)  # Scale iterations with the loop index
        job_id, prefix = call_wsclean(working_dir, msname, imagename, logger, niter, 'CORRECTED_DATA')

        # Track imaging job
        job_info = [job_id]
        logger.info(f"Imaging job submitted with Job ID: {job_info}")

        # Wait for imaging jobs to finish
        all_successful, failed_jobs = wait_for_jobs_to_finish(job_info, working_dir, logger, prefix)

        if all_successful:
            logger.info("Imaging completed successfully. Proceeding to clean up.")
            job_info = [job_id]
            for job_id in job_info:
                logger.info(f"Cleaning up files for Job ID: {job_id} with prefix: {prefix}")
                cleanup_files(job_id, logger, prefix)
        else:
            logger.error(f"Imaging failed. The following Job IDs had issues: {', '.join(map(str, failed_jobs))}")
            sys.exit(1)

        logger.info(f"Imaging iteration {i + 1} completed successfully.")

    logger.info("Self-calibration and imaging process completed successfully.")

