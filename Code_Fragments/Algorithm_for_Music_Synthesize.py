import copy
import os
import subprocess
import sys
import music21
import random
from music_name_number_set import scale_interval_names
from music_name_number_set import note_name_add_octave_in_reasonable
from music_name_number_set import pitch_index_dict, instrument_name_to_music21_object
from music_name_number_set import chord_pitch_standard_by_interval_dict
from music_name_number_set import chord_inversion_dict
from music_name_number_set import rhythm_44_to_duration_dict, rhythm_38_to_duration_dict
from music_name_number_set import answer_index_to_options_dict
from music_name_number_set import questions_template

from music21 import note, chord, tempo, metadata, pitch, interval
import pseudorandom_tools
import json


def create_meta_score(music_title:str ='Music Benchmark Test'):
    new_score = music21.stream.Score(id='MainScore')  # Create and configure metadata
    md = metadata.Metadata()
    md.title = music_title
    new_score.append(md)
    return new_score


def run_xml2abc(output_abc_dir:str="music_theory_examination",
                intput_xml_file_path:str="music_theory_examination/note_A4_to_C5_bpm_60.xml"):
    # python xml2abc.py -d 8 -x -o output_abc_files demo.xml
    cmd = [
        sys.executable,  # Use the current Python interpreter to avoid environment inconsistency issues.
        "xml2abc.py",
        "-d", "8",
        "-x",
        "-o", output_abc_dir,
        intput_xml_file_path       # The path of the input XML file
    ]
    try:
        result = subprocess.run(cmd,check=True,capture_output=True,encoding='utf-8')
    except FileNotFoundError as e:
        print(f"xml2abc execution failed: Unable to find the specified file {e}")

    except subprocess.CalledProcessError as e:
        print(f"The xml2abc script execution failed and the return code is: {e.returncode}")
        print(e.stderr)

    except Exception as e:
        print(f"xml2abc execution failed: unknown error {e}")


def load_dict_from_json(json_file_path):
    """
    Read the content from the JSON file and parse it into a dictionary
    :param json_file_path: JSON file path
    :return: The parsed dictionary (returns an empty dictionary if reading fails)
    """
    if not os.path.exists(json_file_path):
        print(f"ERR! file {json_file_path} not found")
        return {}
    if not os.path.isfile(json_file_path):
        print(f"ERR: {json_file_path} Not an effective document (it's a directory)")
        return {}
    try:
        with open(json_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        else:
            print(f"Warning: The content of the JSON file is not of dictionary type; its actual type is {type(data)}")
            return {}
    except json.JSONDecodeError:
        print(f"Err, {json_file_path} Not in a valid JSON format")
        return {}
    except PermissionError:
        print(f"Correct translation: No permission to read the file {json_file_path}")
        return {}
    except Exception as e:
        print(f"Error: Failed to read JSON file {e}")
        return {}


def run_midi_to_audio(midi_file_path, save_dir, m_name, sound_font = "sf2_files/compound.sf2"):
    audio_file = os.path.join(save_dir, m_name)  + ".wav"
    try:
        result = subprocess.run(
            ["fluidsynth", "-F", audio_file, sound_font, midi_file_path],
            check = True, capture_output = True, encoding = 'utf-8'
        )
    except FileNotFoundError as e:
        print(f"file not find: {e}")
    except Exception as e:
        print(e)


def gen_pitch_list(start_p: str = 'G', start_octave: int = 3, end_p: str = 'G', end_octave: int = 5):
    """
    Generate a list of pitches within the specified pitch range (including augmented ##/diminished --),
    return the list in string form, integer (MIDI) form, and a dictionary mapping numbers to equivalent name pitches.

    Parameters：
        start_p: start pitch（如'G'/'C##'/'D--'），Include this musical pitch
        start_octave: The starting octave (e.g. 3), including that octave
        end_p: end pitch（如'G'/'C##'/'D--'）,include this end pitch
        end_octave: The end octave (e.g. 3), including that octave

    Return：
        str_pitches: A list of pitches in string form
        int_pitches: List of pitches in integer (MIDI) format.
        number_to_name: A dictionary mapping digital pitch to equivalent name list.
    """

    index_to_pitches = {}
    for pitch_name, index in pitch_index_dict.items():
        if index not in index_to_pitches:
            index_to_pitches[index] = []
        if pitch_name not in index_to_pitches[index]:
            index_to_pitches[index].append(pitch_name)
    index_to_pitches = {k: v for k, v in sorted(index_to_pitches.items())}

    start_index = pitch_index_dict[start_p]
    end_index = pitch_index_dict[end_p]

    str_pitches = []
    int_pitches = []
    number_to_name = {}

    for octave in range(start_octave, end_octave + 1):
        if octave == start_octave:
            current_indexes = range(start_index, 12)
        elif octave == end_octave:
            current_indexes = range(0, end_index + 1)
        else:
            current_indexes = range(0, 12)

        for idx in current_indexes:
            pitch_names = index_to_pitches[idx]
            midi_num = 12 * (octave + 1) + idx
            pitch_str_list = [f"{pn}{octave}" for pn in pitch_names]
            str_pitches.extend(pitch_str_list)
            int_pitches.extend([midi_num] * len(pitch_str_list))
            number_to_name[midi_num] = pitch_str_list

    return str_pitches, int_pitches, number_to_name


def single_note_pitch_listening_synthesize(
        standard_pitch,
        target_pitch,
        bpm:int = 60,
        time_signature:str='4/4',
        music_key:int=0,
        note_instrument:str='piano',
        save_dir:str='music_theory_examination/notes',
        synthesize_audio:bool=True,
        convert_abc:bool=True,
        read_abc_question = False
):
    music_score = create_meta_score()

    p0 = music21.stream.Part(id='part0')
    p0.append(music21.meter.TimeSignature(time_signature))
    p0.append(music21.key.KeySignature(music_key))
    p0.append(instrument_name_to_music21_object[note_instrument])
    p0.append(tempo.MetronomeMark(number=bpm))

    note_standard_pitch = note.Note(standard_pitch, type='quarter')
    note_standard_pitch.volume.velocity = 100
    note_target_pitch = note.Note(target_pitch, type='quarter')
    note_target_pitch.volume.velocity = 100

    if not read_abc_question:
        p0.append(note_standard_pitch)
        p0.append(note.Rest('quarter'))
    p0.append(note_target_pitch)

    music_score.append(p0)

    music_name = f"note_{standard_pitch}_to_{target_pitch}_bpm_{bpm}"

    os.makedirs(save_dir, exist_ok=True)

    xml_file_path = os.path.join(save_dir, music_name) + '.xml'
    midi_file_path = os.path.join(save_dir, music_name) + '.mid'

    music_score.write(fmt='xml', fp=xml_file_path)
    music_score.write(fmt='midi', fp=midi_file_path)

    if convert_abc:
        print('convert abc from xml file')
        run_xml2abc(output_abc_dir=save_dir,intput_xml_file_path=xml_file_path)

    if not read_abc_question:
        if synthesize_audio:
            print('synthesize audio from midi file')
            run_midi_to_audio(midi_file_path, save_dir, music_name)


def harmonic_interval_listening_synthesize(
        standard_pitch:int = 'A4', # 69
        base_pitch:str = 'F4',
        interval_type:str = 'Major Third',
        # second_pitch:str = 'B4',
        bpm:int = 60,
        time_signature:str='4/4',
        music_key:int=0,
        note_instrument:str='piano',
        save_dir:str='static/music_theory_examination/interval',
        synthesize_audio:bool=True,
        convert_abc:bool=True,
        read_abc_question=False
):
    # The interval relationship that produces two simultaneous sounds
    music_score = create_meta_score()

    p0 = music21.stream.Part(id='part0')
    p0.append(music21.meter.TimeSignature(time_signature))
    p0.append(music21.key.KeySignature(music_key))
    p0.append(instrument_name_to_music21_object[note_instrument])
    p0.append(tempo.MetronomeMark(number=bpm))

    note_standard_pitch = note.Note(standard_pitch, type='half')
    note_standard_pitch.volume.velocity = 100

    try:
        music21_interval_event = music21.interval.Interval(interval_type)
        second_pitch = music21_interval_event.transposePitch(pitch.Pitch(base_pitch))

        interval_chord = chord.Chord([base_pitch, second_pitch.nameWithOctave])
        interval_chord.duration.type = 'half'
        interval_chord.volume.velocity = 100

        if not read_abc_question:
            p0.append(note_standard_pitch)

        p0.append(interval_chord)
        music_score.append(p0)

        if '-' in base_pitch:
            replace_base_pitch = base_pitch.replace('-','b')
        else:
            replace_base_pitch = base_pitch

        if '-' in second_pitch.nameWithOctave:
            replace_second_pitch = second_pitch.nameWithOctave.replace('-','b')
            # print(second_pitch)
        else:
            replace_second_pitch = second_pitch.nameWithOctave

        music_name = f"interval_{replace_base_pitch}_and_{replace_second_pitch}_{interval_type}_bpm_{bpm}"

        xml_file_path = os.path.join(save_dir, music_name) + '.xml'
        midi_file_path = os.path.join(save_dir, music_name) + '.mid'

        os.makedirs(save_dir, exist_ok=True)

        music_score.write(fmt='xml', fp=xml_file_path)
        music_score.write(fmt='midi', fp=midi_file_path)

        if not read_abc_question:
            if synthesize_audio:
                # print('synthesize audio from midi file')
                run_midi_to_audio(midi_file_path, save_dir, music_name)

        if convert_abc:
            # print('convert abc from xml file')
            run_xml2abc(output_abc_dir=save_dir,intput_xml_file_path=xml_file_path)

        return replace_base_pitch, replace_second_pitch, interval_type

    except Exception as e:
        print(e)


def chord_inversion(chord_list, inversion):
    """
    Program for calculating the transposition sequence of chords
    :param chord_list: The basic sequence of the chord's notes
    :param inversion: Transposition types, such as: 'First Transposition', 'Second Transposition', 'Third Transposition'
    :return: The transposed chord sequence (in ascending order)
    """

    # 1. Verify the validity of the transposition type
    if inversion not in chord_inversion_dict:
        valid_types = list(chord_inversion_dict.keys())
        raise ValueError(f"Transposition type error! Available types:{valid_types}")

    # 2. Verify the chord length of the third inversion (only applicable to four-note chords)
    move_count = chord_inversion_dict[inversion]
    if inversion == 'third inversion' and len(chord_list) != 4:
        raise ValueError(
            f"The third inversion is only applicable to four-note chords, The current chord length is: {len(chord_list)}"
        )

    # 3. The verification of transposition times shall not exceed the maximum supported transposition
    # times of the chord (for example, for a 3-note chord, the maximum transposition is 2 times).
    if move_count >= len(chord_list):
        max_inversion = len(chord_list) - 1
        raise ValueError(f"The chord list contains {len(chord_list)} notes and supports a maximum of {max_inversion} inversions. The inversion {inversion} cannot be performed.")

    # 4. Core transposition logic: Copy the original list → Shift the first N elements up by an octave → Sort
    new_chord = chord_list.copy()
    for i in range(move_count):
        pitch_part = chord_list[i][:-1]
        octave_part = chord_list[i][-1]
        new_octave = int(octave_part) + 1
        new_chord[i] = f"{pitch_part}{new_octave}"
        # new_chord[i] += 12  # Raise the pitch by one octave (12 semitones), when indicated by the pitch number.

    note_priority = {'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6}
    # Custom sorting rule: First sort by octave (the last digit is converted to an integer), then by the priority of note names
    sorted_list = sorted(
        new_chord,
        key=lambda x: (int(x[-1]),  # First sorting key: Octave value (e.g. the 3 in 'G#3')
                       note_priority[x[0]])  # Second sorting key: Note name priority (for example, the G in 'G#3' corresponds to 4)
    )

    return sorted_list


def chord_label_to_pitch(tonality, chord_name, inversion):
    root_pitch = pitch.Pitch(tonality)

    # Obtain the list of intervals corresponding to this chord type
    interval_names = chord_pitch_standard_by_interval_dict[chord_name]

    chord_notes = []

    # Traverse each interval and generate the corresponding pitch.
    for interval_name in interval_names:
        i = music21.interval.Interval(interval_name)
        note_pitch = i.transposePitch(root_pitch)
        chord_notes.append(note_pitch.nameWithOctave)

    # Final processing of transposition
    if inversion != 'root position':
        if len(chord_notes) == 2:
            if inversion == 'first inversion':
                out_pitch_list = chord_inversion(chord_list=chord_notes, inversion=inversion)
                return chord_notes, out_pitch_list
            else:
                return None, None
        elif len(chord_notes) < 4 and inversion == 'third inversion':
            return None, None
        else:
            out_pitch_list = chord_inversion(chord_list=chord_notes, inversion=inversion)
            return chord_notes, out_pitch_list
    else:
        return chord_notes, chord_notes


def chord_listening_synthesize(
        standard_pitch = 'A4',
        chord_style: str = 'm',
        chord_base_note = 'C3',
        inversion: str = 'root position',
        bpm: int = 60,
        time_signature: str = '4/4',
        music_key: int = 0,
        note_instrument: str = 'piano',
        save_dir: str = 'static/music_theory_examination/chord',
        synthesize_audio: bool = True,
        convert_abc: bool = True,
        read_abc_question=False
):
    music_score = create_meta_score()
    p0 = music21.stream.Part(id='part0')
    p0.append(music21.meter.TimeSignature(time_signature))
    p0.append(music21.key.KeySignature(music_key))
    p0.append(instrument_name_to_music21_object[note_instrument])
    p0.append(tempo.MetronomeMark(number=bpm))

    note_standard_pitch = note.Note(standard_pitch, type='half')
    note_standard_pitch.volume.velocity = 100

    pitch_list, inversion_pitch_list = chord_label_to_pitch(tonality=chord_base_note, chord_name=chord_style, inversion = inversion)

    if inversion_pitch_list is None:
        return None, None
    else:
        target_chord = chord.Chord(inversion_pitch_list)
        target_chord.duration.type = 'half'
        target_chord.volume.velocity = 100

        if not read_abc_question:
            p0.append(note_standard_pitch)
        p0.append(target_chord)
        music_score.append(p0)
        music_name = f"chord_{chord_base_note[:-1]}_{chord_style}_{inversion}_bpm_{bpm}"
        xml_file_path = os.path.join(save_dir, music_name) + '.xml'
        midi_file_path = os.path.join(save_dir, music_name) + '.mid'
        os.makedirs(save_dir, exist_ok=True)
        try:
            music_score.write(fmt='xml', fp=xml_file_path)
            music_score.write(fmt='midi', fp=midi_file_path)
            if not read_abc_question:
                if synthesize_audio:
                    run_midi_to_audio(midi_file_path, save_dir, music_name)
            if convert_abc:
                run_xml2abc(output_abc_dir=save_dir, intput_xml_file_path=xml_file_path)
            return music_name, pitch_list
        except Exception as e:
            print(e)
            return None, None


def gen_scale_pitches(scale_type, root_pitch_str) -> list:
    """
    Derive the complete pitch list for the ascending and descending modes
    """

    root_pitch = pitch.Pitch(note_name_add_octave_in_reasonable[root_pitch_str])

    # Obtain the name of the ascending/descending interval of this mode
    asc_interval_names = scale_interval_names[scale_type]["asc"]
    desc_interval_names = scale_interval_names[scale_type]["desc"]

    # Generate the list of ascending pitch values
    asc_pitches = [root_pitch]  # 起始音
    current_pitch = root_pitch
    for i_name in asc_interval_names:
        next_pitch = current_pitch.transpose(interval.Interval(i_name))
        # print("next_pitch:", next_pitch)
        asc_pitches.append(next_pitch)
        current_pitch = next_pitch

    # 5. Generate the list of desc pitch values
    desc_pitches = []
    current_pitch = asc_pitches[-1]  # Repeat the last sound of the previous line
    for i_name in desc_interval_names:
        next_pitch = current_pitch.transpose(interval.Interval(i_name).reverse())
        # print("next_pitch:", next_pitch)
        desc_pitches.append(next_pitch)
        current_pitch = next_pitch

    full_pitches = asc_pitches + desc_pitches

    full_pitch_names = [p.nameWithOctave for p in full_pitches]

    return full_pitch_names


def scale_listening_synthesize(
        standard_pitch = 'A4',
        base_pitch:str='C',  # There is no octave here, for example, Ab
        scale_type:str="major",
        bpm: int = 60,
        time_signature: str = '4/4',
        note_instrument: str = 'piano',
        save_dir: str = 'static/music_theory_examination/scale',
        synthesize_audio: bool = True,
        convert_abc: bool = True,
        read_abc_question=False
):
    music_score = create_meta_score()
    p0 = music21.stream.Part(id='part0')
    p0.append(music21.meter.TimeSignature(time_signature))

    music_key = music21.key.Key('C')

    p0.append(music_key)
    p0.append(instrument_name_to_music21_object[note_instrument])
    p0.append(tempo.MetronomeMark(number=bpm))

    note_standard_pitch = note.Note(standard_pitch, type='half')
    note_standard_pitch.volume.velocity = 100

    if not read_abc_question:
        p0.append(note_standard_pitch)
        p0.append(note.Rest('half'))

    # Obtain the sequence of pitches of the scale
    pitch_scale_list = gen_scale_pitches(scale_type, base_pitch)

    for pitch_scale in pitch_scale_list:
        p0.append(note.Note(pitch_scale, type='quarter'))

    music_score.append(p0)

    music_name = f"scale_{base_pitch}_{scale_type}_bpm_{bpm}"

    xml_file_path = os.path.join(save_dir, music_name) + '.xml'
    midi_file_path = os.path.join(save_dir, music_name) + '.mid'

    os.makedirs(save_dir, exist_ok=True)

    music_score.write(fmt='xml', fp=xml_file_path)
    music_score.write(fmt='midi', fp=midi_file_path)

    if not read_abc_question:
        if synthesize_audio:
            run_midi_to_audio(midi_file_path, save_dir, music_name)

    if convert_abc:
        run_xml2abc(output_abc_dir=save_dir, intput_xml_file_path=xml_file_path)


def rhythmic_pattern_listening_synthesize(
        rhythmic_pattern_str=None,
        bpm: int = 60,
        time_signature: str = '4/4',
        music_key: int = 0,
        note_instrument: str = 'piano',
        save_dir: str = 'static/music_theory_examination/rhythm',
        synthesize_audio: bool = True,
        convert_abc: bool = True
):
    if rhythmic_pattern_str is None and time_signature == '4/4':
        rhythmic_pattern_str = "x2xx  xx2x  xxxx  x2x2 x3x  xx3  (3x2x2x2  x4]"
        # Outputting "abc" will automatically add section symbols.
    elif rhythmic_pattern_str is None and time_signature == '6/8':
        rhythmic_pattern_str = "x2x2x2 xxx2x2 x2x2x2 xxx2x2]"

    if time_signature == '4/4':
        rhythm_to_duration_list = rhythm_44_to_duration_dict
        ts_name = '44'
    elif time_signature == '6/8':
        rhythm_to_duration_list = rhythm_38_to_duration_dict
        ts_name = '68'
    else:
        rhythm_to_duration_list = rhythm_44_to_duration_dict
        ts_name = '44'

    music_score = create_meta_score()
    p0 = music21.stream.Part(id='part0')
    p0.append(music21.meter.TimeSignature(time_signature))
    p0.append(music21.key.KeySignature(music_key))
    p0.append(instrument_name_to_music21_object[note_instrument])
    p0.append(tempo.MetronomeMark(number=bpm))

    split_rhythmic_pattern_str = rhythmic_pattern_str.split()
    rhythm_chinese_name_full = ""
    for rhythm in split_rhythmic_pattern_str:
        if rhythm in rhythm_to_duration_list:
            duration_list = rhythm_to_duration_list[rhythm]
            # rhythm_chinese_name = rhythm_abc_to_chinese_name[rhythm]
            rhythm_chinese_name_full = rhythm_chinese_name_full + rhythm + '_'
            # print(f'rhythm: {rhythm}, duration_list: {duration_list}')
            for duration in duration_list:
                n=music21.note.Note(69)
                n.duration.quarterLength = duration
                p0.append(copy.deepcopy(n))

    music_score.append(p0)

    music_name = f"rhythm_{rhythm_chinese_name_full}bpm_{bpm}_ts_{ts_name}"

    xml_file_path = os.path.join(save_dir, music_name) + '.xml'
    midi_file_path = os.path.join(save_dir, music_name) + '.mid'

    os.makedirs(save_dir, exist_ok=True)

    music_score.write(fmt='xml', fp=xml_file_path)
    music_score.write(fmt='midi', fp=midi_file_path)

    if synthesize_audio:
        run_midi_to_audio(midi_file_path, save_dir, music_name)

    if convert_abc:
        run_xml2abc(output_abc_dir=save_dir, intput_xml_file_path=xml_file_path)

    wav_file_path = os.path.join(save_dir, music_name) + '.wav'

    return wav_file_path


def randomly_make_music_theory_questions(
        process_idx,
        input_seed,
        seed,
        q_number,
        music_theory_questions_jsonl_path="static/music_theory_examination/music_theory_questions/music_theory_questions_cn.jsonl"
):

    music_theory_datas = []

    with open(music_theory_questions_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            json_dict = json.loads(line)
            music_theory_datas.append(json_dict)

    random.seed(seed)
    random.sample(music_theory_datas, 3)

    select_question, select_question_idx = pseudorandom_tools.select_element_by_seed(music_theory_datas, seed)
    # Choose only one question. As long as the seeds are different, the selected question will also be different.

    # "Answer" refers to the correct solution, while "options" represent the distractors.
    all_options = select_question["options"]
    all_options.append(select_question["answer"])

    random.shuffle(all_options)

    answer_index = all_options.index(select_question["answer"])

    # make question
    s_q = select_question['question']
    question = copy.deepcopy(questions_template)
    question["id"] = f"Music Theory Concepts_{input_seed}_{q_number}_{process_idx}"
    question["seed"] = input_seed
    question["local_seed"] = seed
    question["question"] = s_q
    question["task"] = "Music Theory Concepts"
    question["modality"] = "text"
    question["source"] = "https://viva.pressbooks.pub/openmusictheorycopy"
    question["task_idx"] = q_number
    question["options"] = {"A": all_options[0], "B": all_options[1], "C": all_options[2], "D": all_options[3]}
    question["answer"] = answer_index_to_options_dict[answer_index]
    question["audio_path"] = None
    question["score_path"] = None
    return question


if __name__ == '__main__':
    scale_listening_synthesize(
        base_pitch= 'C',
        scale_type = "chromatic",
        save_dir = 'static/music_theory_examination/scale',
        convert_abc = True,
        read_abc_question = True
    )
