import struct


def sci_to_bytes(data: list):

    msg = bytearray((data[0] + '\r\n').encode('ascii'))

    for arg in data[1:]:

        if isinstance(arg, bool):
            msg += b'\x01' if arg else b'\x00'

        elif isinstance(arg, int):
            msg += arg.to_bytes(8, 'little')

        elif isinstance(arg, float):
            msg += struct.pack('f', arg)

        elif isinstance(arg, str):
            msg += len(arg).to_bytes(4, 'little')
            msg += bytearray(arg.encode('ascii'))

    return msg


# general commands
def get_instances(plugin_id: str):
    return ["sci::GetInstances", plugin_id]


def get_all_instances():
    return ["sci::GetAllInstances"]


def get_profile_type():
    return ["sci::GetProfileType"]


# laser commands
def set_laser_emission(deviceSN: str, description: str, on_off: bool):
    return ["Laser::SetEmission", deviceSN, description, on_off]


def set_laser_shutter(deviceSN: str, open_close: bool):
    return ["Laser::SetShutter", deviceSN, open_close]


def set_laser_intensity_percentage(deviceSN: str, description: str, intensity: float):
    return ["Laser::SetIntensity", deviceSN, description, intensity]


def get_laser_lightsources():
    return ["Laser::GetLightsources"]


def get_laser_lightsource_status(deviceSN: str, description: str):
    return ["Laser::GetLightsourceStatus", deviceSN, description]


# sequence manager commands
def get_sequences():
    return ["Sequence manager::GetSequences"]


def select_sequence(filepath: str):
    return ["Sequence manager::SelectSequence", filepath]


def import_sequence(filepath: str, target_directory: str):
    return ["Sequence manager::ImportSequence", filepath, target_directory]


def delete_sequence(filepath: str):
    return ["Sequence manager::DeleteSequence", filepath]


# UGA-42 commands
def get_uga42_state():
    return ["UGA-42::GetState"]


def upload_uga42_sequence():
    return ["UGA-42::UploadSequence"]


def run_uga42_sequence(runs: int, start_condition: str, trigger_behav: str):
    return ["UGA-42::RunSequence", runs, start_condition, trigger_behav]


def stop_uga42_sequence():
    return ["UGA-42::StopSequence"]


# holo4D commands
def get_holo4d_state():
    return ["Holo4D::GetState"]


def upload_holo4d_sequence(runs: int):
    return ["Holo4D::UploadSequence", runs]


def run_holo4d_sequence(start_condition: str, trigger_behav: str):
    return ["Holo4D::RunSequence", start_condition, trigger_behav]


def stop_holo4d_sequence():
    return ["Holo4D::StopSequence"]
