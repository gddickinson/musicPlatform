import numpy as np
import pyaudio
import threading
import queue
import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class AudioBlock:
    """Base class for all audio processing blocks in the system"""
    def __init__(self, name="AudioBlock"):
        self.name = name
        self.inputs = []  # List of input blocks
        self.outputs = []  # List of output blocks
        self.muted = False
        self.solo = False
        self.volume = 1.0
        self.bypass = False
        self.buffer = np.zeros(1024)  # Default buffer size
        self.sample_rate = 44100
        
    def process(self, buffer_size=1024):
        """Process audio and return the result"""
        if self.muted:
            return np.zeros(buffer_size)
            
        # Process inputs
        if self.inputs:
            # Mix all inputs
            mixed = np.zeros(buffer_size)
            for input_block in self.inputs:
                mixed += input_block.process(buffer_size)
        else:
            # Generate own audio if no inputs
            mixed = self.generate(buffer_size)
            
        # Apply processing
        if not self.bypass:
            processed = self.process_audio(mixed)
        else:
            processed = mixed
            
        # Apply volume
        output = processed * self.volume
        
        # Update internal buffer
        self.buffer = output
        
        return output
        
    def generate(self, buffer_size):
        """Generate audio - override in subclasses that generate sound"""
        return np.zeros(buffer_size)
        
    def process_audio(self, audio):
        """Process audio - override in subclasses that process audio"""
        return audio
        
    def connect_to(self, other_block):
        """Connect this block as input to another block"""
        if other_block not in self.outputs:
            self.outputs.append(other_block)
            
        if self not in other_block.inputs:
            other_block.inputs.append(self)
            
    def disconnect_from(self, other_block):
        """Disconnect this block from another block"""
        if other_block in self.outputs:
            self.outputs.remove(other_block)
            
        if self in other_block.inputs:
            other_block.inputs.remove(self)
            
    def disconnect_all(self):
        """Disconnect from all inputs and outputs"""
        # Disconnect from outputs
        for output in list(self.outputs):
            self.disconnect_from(output)
            
        # Disconnect inputs
        for input_block in list(self.inputs):
            input_block.disconnect_from(self)


class SynthBlock(AudioBlock):
    """Audio block for synthesizers"""
    def __init__(self, name="Synth"):
        super().__init__(name)
        self.oscillators = []
        self.current_notes = {}  # {note_name: frequency}
        
    def add_oscillator(self, waveform="sine", detune=0.0, volume=1.0):
        """Add an oscillator"""
        self.oscillators.append({
            "waveform": waveform,
            "detune": detune,
            "volume": volume,
            "phase": 0.0
        })
        
    def note_on(self, note_name, frequency):
        """Trigger a note on"""
        self.current_notes[note_name] = frequency
        
    def note_off(self, note_name):
        """Trigger a note off"""
        if note_name in self.current_notes:
            del self.current_notes[note_name]
            
    def generate(self, buffer_size):
        """Generate audio from oscillators"""
        if not self.oscillators or not self.current_notes:
            return np.zeros(buffer_size)
            
        output = np.zeros(buffer_size)
        t = np.arange(buffer_size) / self.sample_rate
        
        for note, frequency in self.current_notes.items():
            for osc in self.oscillators:
                # Apply detune
                freq = frequency * (2 ** (osc["detune"] / 1200))  # Detune in cents
                
                # Generate waveform
                if osc["waveform"] == "sine":
                    wave = np.sin(2 * np.pi * freq * t + osc["phase"])
                elif osc["waveform"] == "square":
                    wave = np.sign(np.sin(2 * np.pi * freq * t + osc["phase"]))
                elif osc["waveform"] == "sawtooth":
                    wave = 2 * ((t * freq + osc["phase"]) % 1) - 1
                elif osc["waveform"] == "triangle":
                    wave = 2 * np.abs(2 * ((t * freq + osc["phase"]) % 1) - 1) - 1
                else:
                    wave = np.zeros(buffer_size)
                    
                # Apply volume and add to output
                output += wave * osc["volume"]
                
                # Update phase
                osc["phase"] = (osc["phase"] + buffer_size * freq / self.sample_rate) % 1.0
                
        # Normalize
        if len(self.current_notes) > 0 and len(self.oscillators) > 0:
            output /= len(self.current_notes) * len(self.oscillators)
            
        return output


class SamplerBlock(AudioBlock):
    """Audio block for sample playback"""
    def __init__(self, name="Sampler"):
        super().__init__(name)
        self.samples = {}  # {name: {data: np.array, rate: int}}
        self.playing_samples = []  # [{data: np.array, rate: int, position: int, volume: float}]
        
    def add_sample(self, name, data, sample_rate):
        """Add a sample to the sampler"""
        self.samples[name] = {
            "data": data,
            "rate": sample_rate
        }
        
    def remove_sample(self, name):
        """Remove a sample from the sampler"""
        if name in self.samples:
            del self.samples[name]
            
    def play_sample(self, name, volume=1.0):
        """Trigger sample playback"""
        if name in self.samples:
            sample = self.samples[name]
            self.playing_samples.append({
                "data": sample["data"],
                "rate": sample["rate"],
                "position": 0,
                "volume": volume
            })
            
    def generate(self, buffer_size):
        """Generate audio from playing samples"""
        if not self.playing_samples:
            return np.zeros(buffer_size)
            
        output = np.zeros(buffer_size)
        
        # Process all playing samples
        still_playing = []
        for sample in self.playing_samples:
            # Calculate how many samples to read
            remaining = len(sample["data"]) - sample["position"]
            if remaining <= 0:
                continue  # Skip finished samples
                
            # Calculate rate conversion factor
            rate_ratio = sample["rate"] / self.sample_rate
            
            # Calculate how many samples to read from source
            to_read = min(int(buffer_size * rate_ratio), remaining)
            
            # Read data
            data = sample["data"][sample["position"]:sample["position"] + to_read]
            
            # Resample if necessary
            if rate_ratio != 1.0:
                # Simple linear resampling
                indices = np.linspace(0, len(data) - 1, buffer_size)
                data = np.interp(indices, np.arange(len(data)), data)
            elif len(data) < buffer_size:
                # Pad with zeros
                data = np.pad(data, (0, buffer_size - len(data)))
                
            # Add to output
            output += data * sample["volume"]
            
            # Update position
            sample["position"] += to_read
            
            # Keep track of samples still playing
            if sample["position"] < len(sample["data"]):
                still_playing.append(sample)
                
        # Update playing samples list
        self.playing_samples = still_playing
        
        return output


class EffectBlock(AudioBlock):
    """Base class for audio effects"""
    def __init__(self, name="Effect"):
        super().__init__(name)
        
    def process_audio(self, audio):
        """Process audio - override in subclasses"""
        return audio


class DelayEffect(EffectBlock):
    """Delay effect"""
    def __init__(self, name="Delay", delay_time=0.5, feedback=0.5, mix=0.5):
        super().__init__(name)
        self.delay_time = delay_time  # Delay time in seconds
        self.feedback = feedback      # Feedback amount (0-1)
        self.mix = mix                # Wet/dry mix (0-1)
        self.delay_buffer = None
        self.delay_samples = 0
        self.buffer_pos = 0
        
    def process_audio(self, audio):
        if self.delay_samples != int(self.delay_time * self.sample_rate):
            # Update delay buffer size if delay time changed
            self.delay_samples = int(self.delay_time * self.sample_rate)
            self.delay_buffer = np.zeros(self.delay_samples)
            self.buffer_pos = 0
            
        output = np.zeros_like(audio)
        
        for i in range(len(audio)):
            # Read from delay buffer
            delayed_sample = self.delay_buffer[self.buffer_pos]
            
            # Mix dry and wet signals
            output[i] = audio[i] * (1 - self.mix) + delayed_sample * self.mix
            
            # Write to delay buffer
            self.delay_buffer[self.buffer_pos] = audio[i] + delayed_sample * self.feedback
            
            # Update buffer position
            self.buffer_pos = (self.buffer_pos + 1) % self.delay_samples
            
        return output


class ReverbEffect(EffectBlock):
    """Simple reverb effect"""
    def __init__(self, name="Reverb", room_size=0.8, damping=0.5, mix=0.5):
        super().__init__(name)
        self.room_size = room_size  # Room size (0-1)
        self.damping = damping      # Damping factor (0-1)
        self.mix = mix              # Wet/dry mix (0-1)
        self.reverb_buffer = np.zeros(int(2 * self.sample_rate))  # 2 second buffer
        
    def process_audio(self, audio):
        output = np.zeros_like(audio)
        buffer_length = len(self.reverb_buffer)
        
        for i in range(len(audio)):
            # Calculate reverb
            reverb_sample = 0
            for j in range(8):  # Use 8 reflections
                delay = int(buffer_length * (0.2 + 0.1 * j) * self.room_size) % buffer_length
                idx = (i - delay) % buffer_length
                reverb_sample += self.reverb_buffer[idx] * (1 - self.damping) ** j
                
            # Mix dry and wet signals
            output[i] = audio[i] * (1 - self.mix) + reverb_sample * self.mix
            
            # Update reverb buffer
            self.reverb_buffer[i % buffer_length] = audio[i]
            
        return output


class FilterEffect(EffectBlock):
    """Simple filter effect"""
    def __init__(self, name="Filter", cutoff=1000, resonance=0.5, filter_type="lowpass"):
        super().__init__(name)
        self.cutoff = cutoff            # Cutoff frequency in Hz
        self.resonance = resonance      # Resonance (0-1)
        self.filter_type = filter_type  # "lowpass", "highpass", "bandpass"
        self.x1 = 0
        self.x2 = 0
        self.y1 = 0
        self.y2 = 0
        self.calculate_coefficients()
        
    def calculate_coefficients(self):
        """Calculate filter coefficients"""
        # Normalize cutoff frequency
        f = self.cutoff / self.sample_rate
        f = max(0.001, min(0.499, f))  # Clamp between 0.001 and 0.499
        
        # Calculate resonance
        q = 1.0 - self.resonance
        q = max(0.01, min(1.0, q))  # Clamp between 0.01 and 1.0
        
        # Calculate coefficients
        k = 0.5 * np.sin(np.pi * f) / q
        
        if self.filter_type == "lowpass":
            # Lowpass filter
            norm = 1.0 / (1.0 + k + k * k)
            self.a0 = k * k * norm
            self.a1 = 2 * self.a0
            self.a2 = self.a0
            self.b1 = 2.0 * (k * k - 1.0) * norm
            self.b2 = (1.0 - k + k * k) * norm
        elif self.filter_type == "highpass":
            # Highpass filter
            norm = 1.0 / (1.0 + k + k * k)
            self.a0 = 1.0 * norm
            self.a1 = -2.0 * self.a0
            self.a2 = self.a0
            self.b1 = 2.0 * (k * k - 1.0) * norm
            self.b2 = (1.0 - k + k * k) * norm
        elif self.filter_type == "bandpass":
            # Bandpass filter
            norm = 1.0 / (1.0 + k + k * k)
            self.a0 = k * norm
            self.a1 = 0.0
            self.a2 = -self.a0
            self.b1 = 2.0 * (k * k - 1.0) * norm
            self.b2 = (1.0 - k + k * k) * norm
            
    def process_audio(self, audio):
        output = np.zeros_like(audio)
        
        for i in range(len(audio)):
            # Apply filter
            output[i] = (
                self.a0 * audio[i] + 
                self.a1 * self.x1 + 
                self.a2 * self.x2 - 
                self.b1 * self.y1 - 
                self.b2 * self.y2
            )
            
            # Update filter state
            self.x2 = self.x1
            self.x1 = audio[i]
            self.y2 = self.y1
            self.y1 = output[i]
            
        return output


class CompressorEffect(EffectBlock):
    """Dynamic range compressor"""
    def __init__(self, name="Compressor", threshold=-20, ratio=4, attack=0.01, release=0.1):
        super().__init__(name)
        self.threshold = threshold  # Threshold in dB
        self.ratio = ratio          # Compression ratio
        self.attack = attack        # Attack time in seconds
        self.release = release      # Release time in seconds
        self.envelope = 0.0         # Envelope follower
        self.gain_reduction = 0.0   # Current gain reduction in dB
        
    def process_audio(self, audio):
        output = np.zeros_like(audio)
        
        # Convert threshold from dB to linear
        threshold_linear = 10 ** (self.threshold / 20)
        
        # Calculate attack and release coefficients
        attack_coef = np.exp(-1 / (self.sample_rate * self.attack))
        release_coef = np.exp(-1 / (self.sample_rate * self.release))
        
        for i in range(len(audio)):
            # Calculate envelope (simple peak detector)
            input_abs = np.abs(audio[i])
            if input_abs > self.envelope:
                self.envelope = attack_coef * self.envelope + (1 - attack_coef) * input_abs
            else:
                self.envelope = release_coef * self.envelope + (1 - release_coef) * input_abs
                
            # Skip compression if below threshold
            if self.envelope <= threshold_linear:
                self.gain_reduction = 0.0
            else:
                # Calculate gain reduction in dB
                input_db = 20 * np.log10(self.envelope + 1e-10)
                output_db = self.threshold + (input_db - self.threshold) / self.ratio
                self.gain_reduction = output_db - input_db
                
            # Apply gain reduction
            gain = 10 ** (self.gain_reduction / 20)
            output[i] = audio[i] * gain
            
        return output


class AudioSystem(QObject):
    """
    Central audio system that manages audio routing, processing, and playback.
    """
    audioProcessed = pyqtSignal(np.ndarray)  # Signal emitted when audio is processed
    
    def __init__(self, sample_rate=44100, buffer_size=1024):
        super().__init__()
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.blocks = {}  # Dictionary of audio blocks by name
        self.master_block = None  # Master output block
        self.running = False
        self.audio_queue = queue.Queue(maxsize=10)  # Queue for audio blocks
        
        # PyAudio setup
        self.pyaudio = pyaudio.PyAudio()
        self.stream = None
        
    def add_block(self, block, name=None):
        """Add an audio block to the system"""
        if name is None:
            name = block.name
            
        # Make sure name is unique
        if name in self.blocks:
            i = 1
            while f"{name}_{i}" in self.blocks:
                i += 1
            name = f"{name}_{i}"
            
        block.name = name
        block.sample_rate = self.sample_rate
        self.blocks[name] = block
        
        return block
        
    def remove_block(self, name):
        """Remove an audio block from the system"""
        if name in self.blocks:
            block = self.blocks[name]
            block.disconnect_all()
            del self.blocks[name]
            
    def connect_blocks(self, source_name, dest_name):
        """Connect two audio blocks"""
        if source_name in self.blocks and dest_name in self.blocks:
            source = self.blocks[source_name]
            dest = self.blocks[dest_name]
            source.connect_to(dest)
            
    def disconnect_blocks(self, source_name, dest_name):
        """Disconnect two audio blocks"""
        if source_name in self.blocks and dest_name in self.blocks:
            source = self.blocks[source_name]
            dest = self.blocks[dest_name]
            source.disconnect_from(dest)
            
    def set_master_block(self, name):
        """Set the master output block"""
        if name in self.blocks:
            self.master_block = self.blocks[name]
            
    def create_default_setup(self):
        """Create a default audio system setup"""
        # Create master output block
        master = AudioBlock("Master")
        self.add_block(master)
        self.master_block = master
        
        # Create synth block
        synth = SynthBlock("Synth")
        synth.add_oscillator("sine")
        self.add_block(synth)
        synth.connect_to(master)
        
        # Create sampler block
        sampler = SamplerBlock("Sampler")
        self.add_block(sampler)
        sampler.connect_to(master)
        
        # Create effect blocks
        delay = DelayEffect("Delay")
        self.add_block(delay)
        
        reverb = ReverbEffect("Reverb")
        self.add_block(reverb)
        
        # Set up effects chain: synth -> delay -> reverb -> master
        synth.disconnect_all()
        synth.connect_to(delay)
        delay.connect_to(reverb)
        reverb.connect_to(master)
        
        # Also connect sampler directly to master
        sampler.connect_to(master)
        
    def start(self):
        """Start audio processing and playback"""
        if self.running:
            return
            
        # Make sure we have a master block
        if not self.master_block:
            if not self.blocks:
                self.create_default_setup()
            else:
                # Use the first block as master
                self.master_block = list(self.blocks.values())[0]
                
        # Set up PyAudio callback
        def callback(in_data, frame_count, time_info, status):
            # Process audio
            if self.master_block:
                output = self.master_block.process(frame_count)
                
                # Make sure output is the right size
                if len(output) < frame_count:
                    output = np.pad(output, (0, frame_count - len(output)))
                elif len(output) > frame_count:
                    output = output[:frame_count]
                    
                # Convert to float32
                output = output.astype(np.float32)
                
                # Emit signal with processed audio
                self.audioProcessed.emit(output)
                
                return (output.tobytes(), pyaudio.paContinue)
            else:
                # Return silence if no master block
                return (np.zeros(frame_count, dtype=np.float32).tobytes(), pyaudio.paContinue)
                
        # Start stream
        self.stream = self.pyaudio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=self.buffer_size,
            stream_callback=callback
        )
        
        self.stream.start_stream()
        self.running = True
        
    def stop(self):
        """Stop audio processing and playback"""
        if not self.running:
            return
            
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        self.running = False
        
    def get_waveform(self):
        """Get the current output waveform"""
        if self.master_block:
            return self.master_block.buffer
        else:
            return np.zeros(self.buffer_size)
            
    def close(self):
        """Close the audio system"""
        self.stop()
        self.pyaudio.terminate()
        

# Examples of how to use the audio system

# Create an audio system
# audio_system = AudioSystem()

# Create some audio blocks
# synth = SynthBlock("LeadSynth")
# synth.add_oscillator("sawtooth")
# synth.add_oscillator("square", detune=10.0, volume=0.5)
# audio_system.add_block(synth)

# Add an effect
# reverb = ReverbEffect("Reverb", room_size=0.8, mix=0.3)
# audio_system.add_block(reverb)

# Connect blocks
# audio_system.connect_blocks("LeadSynth", "Reverb")
# audio_system.connect_blocks("Reverb", "Master")

# Trigger a note
# synth.note_on("C4", 261.63)  # Middle C

# Start audio processing
# audio_system.start()

# Stop after a while
# import time
# time.sleep(2)
# synth.note_off("C4")
# time.sleep(1)
# audio_system.stop()
# audio_system.close()