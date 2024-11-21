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


from .pokedex import *


def main():
    start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tech_log = 'selfcal_{}.log'.format(start_time)

    logger = configure_logger('charizard-vla', tech_log)


    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run PokeEgg with a configuration file.")
    parser.add_argument("config_file", help="Path to the configuration file.")
    args = parser.parse_args()

    # Parse the configuration file
    config_file = args.config_file
    params = parse_config(config_file)

    # Print parsed configuration for debugging or confirmation
    print("Configuration Parameters:")
    for key, value in params.items():
        print(f"{key}: {value}")

    # Initialize necessary variables
    working_dir = params['working_dir']
    ms_in = params['msname']  # Example: input measurement set
    vla_pipe_dir = params['vla_pipe_dir']  # Path to VLA pipeline directory
    logger = logging.getLogger("CalibrationLogger")

    # Perform calibration
    job_id, prefix = initial_calibration(working_dir, ms_in, vla_pipe_dir, logger, 'initial_cal')

    # Track calibration job
    job_info = [job_id]
    logger.info(f"Calibration job submitted with Job ID: {job_info}")

    # Wait for calibration jobs to finish
    all_successful, failed_jobs = wait_for_jobs_to_finish(job_info, working_dir, logger, prefix)

    if all_successful:
        logger.info("Calibration completed successfully. Proceeding to clean up.")
        # Clean up files related to calibration
        job_info = [job_id]
        for job_id in job_info:
            logger.info(f"Cleaning up files for Job ID: {job_id} with prefix: {prefix}")
            cleanup_files(job_id, logger, prefix)
    else:
        logger.error(f"Calibration failed. The following Job IDs had issues: {', '.join(map(str, failed_jobs))}")
        sys.exit(1)

    logger.info(f"Calibration iteration completed. Proceeding to fine-tuning.")

    latest_casa_log = find_latest_log(working_dir)
    flux_density, a_1, a_2, freq_GHz = extract_setjy_params(latest_casa_log,params['leakcal'])
    leakcal_source = params['leakcal']

    # Construct the leakage calibrator dictionary
    leakcal_dict = {
        "source": '{}'.format(leakcal_source),
        "reffreq": f"{freq_GHz}GHz",  # Reference frequency in GHz
        "stokes_I": flux_density,  # Stokes I flux density
        "spectral_index": [a_1, a_2],  # Spectral index coefficient
    }

    if params['pacal'] == '3C286':
        pacal_dict = {
                "source": "3C286",
                "reffreq": "1.0GHz",  # Reference Frequency for fit values
                "stokes_I": 17.62458670336218,  # Stokes I flux density
                "spectral_index": [-0.45303, -0.14583],  # Spectral Index (alpha)
                "polarization_fraction": [0.08669298, 0.02326563, -0.00804815, 0.00101985],  # Polarization Fraction
                "polarization_angle": [0.574826698, 0.000840913228, -0.000187630947]  # Polarization Angle
        }
    else:
        logger.error("Supply polarization angle calibrator.")

    
    casa_dir  = params['casa_dir']
    job_id, prefix = refine_calibration(working_dir, ms_in, casa_dir, logger, pacal_dict, leakcal_dict, 'refine_cal')

    # Track calibration job
    job_info = [job_id]
    logger.info(f"Refining calibration job submitted with Job ID: {job_info}")

    # Wait for calibration jobs to finish
    all_successful, failed_jobs = wait_for_jobs_to_finish(job_info, working_dir, logger, prefix)

    if all_successful:
        logger.info("Polarization Calibration completed successfully. Proceeding to clean up.")
        # Clean up files related to calibration
        job_info = [job_id]
        for job_id in job_info:
            logger.info(f"Cleaning up files for Job ID: {job_id} with prefix: {prefix}")
            cleanup_files(job_id, logger, prefix)
    else:
        logger.error(f"Calibration failed. The following Job IDs had issues: {', '.join(map(str, failed_jobs))}")
        sys.exit(1)

    logger.info(f"Refinement done, as well as the polarization calibration")

    selfcal_bool = params['selfcal']
    ms_in = params['starting_ms']
    ms_out = params['split_ms']
    chanaverage = params['chanaverage']
    chanbin = params['chanbin']
    target = params['target']
    if selfcal_bool:
        job_id, prefix = splitting_ms(ms_in, ms_out, casa_dir, logger, '', chanaverage, chanbin, target, 'split_ms')

        # Track calibration job
        job_info = [job_id]
        logger.info(f"Splitting fields.....: {job_info}")

        # Wait for calibration jobs to finish
        all_successful, failed_jobs = wait_for_jobs_to_finish(job_info, working_dir, logger, prefix)

        if all_successful:
            logger.info("Splitted the MS.")
            # Clean up files related to calibration
            job_info = [job_id]
            for job_id in job_info:
                logger.info(f"Cleaning up files for Job ID: {job_id} with prefix: {prefix}")
                cleanup_files(job_id, logger, prefix)
        else:
            logger.error(f"Splitting failed. The following Job IDs had issues: {', '.join(map(str, failed_jobs))}")
            sys.exit(1)

        logger.info(f"Splitting done, moving onto self-calibration")
        
        solint = params['solint']
        pcal = params['pcal']
        apcal = params['apcal']
        niter_s = params['niter_s']
        ref_ant = params['ref_ant']
        logger.info("Starting self-calibration")
        selfcal(ms_in,working_dir,solint,pcal, apcal, niter_s,logger,casa_dir,ref_ant )
    else:
        logger.info("Ahh, no self-cal!! Do you want to plot? We need more people like you in Radio Astronomy.")





if __name__ == "__main__":
    main()


