# CREATED: 4/23/17 15:37 by Justin Salamon <justin.salamon@nyu.edu>

'''
Utility functions for audio processing using FFMPEG (beyond sox). Based on:
https://github.com/mathos/neg23/
'''

import subprocess
import sox
import numpy as np
import pyloudnorm
import soundfile
import tempfile
from .scaper_exceptions import ScaperError
from .util import _close_temp_files

def get_integrated_lufs(audio_array, samplerate, min_duration=0.5,
                        filter_class='K-weighting', block_size=0.400):
    """
    Returns the integrated LUFS for a numpy array containing
    audio samples.

    For files shorter than 400 ms ffmpeg returns a constant integrated LUFS
    value of -70.0. To avoid this, files shorter than min_duration (by default
    500 ms) are self-concatenated until min_duration is reached and the
    LUFS value is computed for the concatenated file.

    Parameters
    ----------
    audio_array : np.ndarray
        numpy array containing samples or path to audio file for computing LUFS
    samplerate : int
        Sample rate of audio, for computing duration
    min_duration : float
        Minimum required duration for computing LUFS value. Files shorter than
        this are self-concatenated until their duration reaches this value
        for the purpose of computing the integrated LUFS. Caution: if you set
        min_duration < 0.4, a constant LUFS value of -70.0 will be returned for
        all files shorter than 400 ms.
    filter_class : str
        Class of weighting filter used.
        - 'K-weighting' (default)
        - 'Fenton/Lee 1'
        - 'Fenton/Lee 2'
        - 'Dash et al.'
    block_size : float 
        Gating block size in seconds. Defaults to 0.400.
    
    Returns
    -------
    loudness
        Loudness in terms of LUFS 
    """
    duration = audio_array.shape[0] / float(samplerate)
    if duration < min_duration:
        ntiles = int(np.ceil(min_duration / duration))
        audio_array = np.tile(audio_array, (ntiles, 1))
    meter = pyloudnorm.Meter(
        samplerate, filter_class=filter_class, block_size=block_size
    )
    loudness = meter.integrated_loudness(audio_array)
    loudness = max(loudness, -70)
    return loudness


def match_sample_length(audio_path, duration_in_samples):
    '''
    Takes a path to an audio file and a duration defined in samples. The audio
    is loaded from the specifid audio_path and padded or trimmed such that it
    matches the duration_in_samples. The modified audio is then saved back to
    audio_path. This ensures that the durations match exactly. If the audio
    needed to be padded, it is padded with zeros to the end of the audio file.
    If the audio needs to be trimmed, the function will trim samples from the end of 
    the audio file. The sample rate of the saved audio is the same as the sample 
    rate of the input file.

    Parameters
    ----------
    audio_path : str
        Path to the audio file that will be modified.
    duration_in_samples : int
        Duration that the audio will be padded or trimmed to.

    '''
    if duration_in_samples <= 0:
        raise ScaperError(
            'Duration in samples must be > 0.')
    if not isinstance(duration_in_samples, int):
        raise ScaperError(
            'Duration in samples must be an integer.')

    audio, sr = soundfile.read(audio_path)
    audio_info = soundfile.info(audio_path)
    current_duration = audio.shape[0]

    if duration_in_samples < current_duration:
        audio = audio[:duration_in_samples]
    elif duration_in_samples > current_duration:
        n_pad = duration_in_samples - current_duration

        pad_width = [(0, 0) for _ in range(len(audio.shape))]
        pad_width[0] = (0, n_pad)

        audio = np.pad(audio, pad_width, 'constant')

    soundfile.write(audio_path, audio, sr, 
        subtype=audio_info.subtype, format=audio_info.format)
