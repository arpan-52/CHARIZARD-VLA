# Charizard-VLA

<p align="center">
  <img src="https://github.com/user-attachments/assets/45f93e6e-3d36-4f1c-b5e6-a75c87be92de" width="800">
</p>

**Charizard-VLA**: *Calibration and Highly Automated Radio Imaging with polariZation by Advanced Resource Distribution for VLA*

Charizard-VLA is a powerful and automated pipeline for processing Very Large Array (VLA) data. It integrates the VLA Pipeline, CASA, and WSClean to perform imaging, polarization calibration, and self-calibration with minimal user intervention, delivering high-quality scientific outputs.

---

## Features

- **End-to-End Automation**: Simplifies the complete VLA data reduction workflow.
- **Polarization Calibration**: Processes Stokes parameters for detailed polarization analysis.
- **Self-Calibration**: Enhances image quality with iterative self-calibration.
- **Configurable Workflow**: Modify and control each step via a user-friendly configuration file.
- **High Efficiency**: Optimized to handle large radio astronomy datasets.

---

## Requirements

Before running Charizard-VLA, ensure the following software and system dependencies are installed and configured:

1. **Python**: Version 3.6 or higher.
2. **CASA**: Common Astronomy Software Applications (https://casa.nrao.edu).
3. **WSClean**: A fast wide-field imager (https://wsclean.readthedocs.io).
4. **VLA Pipeline**: NRAO's official pipeline for VLA data processing.
5. **System Resources**: A machine with a PBS job scheduler.

Install Python dependencies via pip:
```bash
pip install charizard-vla
```
## Example config file
```bash 
[DEFAULT]

working_dir = /scratch/process_G71/obs2
msname = obs2_G71.ms
pacal = 3C286
leakcal = J2355+4950
ref_ant = ea10

# Selfcal Parameters....

starting_ms = obs2_G71.ms
split_ms = split-obs2_G71.ms
chanaverage = True
chanbin = 2
target = PSZ2G071+28.86
selfcal = True
selfcal_ms = split-obs2_G71.ms
solint = ['2min','1min','1min']
pcal = 2
apcal = 1
niter_s = 10000
casa_dir = /home/apal/casa-6.6.4-34-py3.8.el8/
vla_pipe_dir = /home/apal/casa-6.5.4-9-pipeline-2023.1.0.124/
```
## To make the CHARIZARD-VLA win the Pokemon battles,
``` bash
charizard-vla config.ini



