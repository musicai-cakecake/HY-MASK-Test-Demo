import random
from Algorithm_for_Music_Synthesize import gen_pitch_list, single_note_pitch_listening_synthesize, harmonic_interval_listening_synthesize
from Algorithm_for_Music_Synthesize import chord_listening_synthesize, load_dict_from_json, scale_listening_synthesize, rhythmic_pattern_listening_synthesize, randomly_make_music_theory_questions
from music_name_number_set import semitones_to_interval_name_full, scale_interval_names, note_name_add_octave_in_reasonable, bpm_name_to_bpm
from music_name_number_set import questions_template

import pseudorandom_tools
import os
import warnings
import json
import copy
import time
from music21 import interval,pitch
from melody_generation.inference import infer_from_loaded_model
from lm_gen_abc_to_audio import batch_gen_melody_file_and_item
from wav_tools import merge_and_adjust_volume


answer_index_to_options_dict = {
    0:"A",
    1:"B",
    2:"C",
    3:"D",
}

all_ts_dict = {
    '2/4': '24',
    '3/4': '34',
    '4/4': '44',
    '3/8': '38',
    '6/8': '68',
}

all_ts = ['2/4', '3/4', '4/4', '3/8', '6/8']


def read_abc_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            abc_content = f.read()  # The "read()" function will completely preserve all newline characters (\n).
        return abc_content
    except FileNotFoundError:
        return f"Error: File not found -> {file_path}"
    except PermissionError:
        return f"No permission to read the file. -> {file_path}"
    except Exception as e:
        return str(e)


def trim_abc_body(abc_full, retain_head=False) -> str:
    def remove_abc_meter(abc_str: str) -> str:
        # Delete the meter field (the entire line starting with "M:", including the newline character) from the ABC string.
        lines = abc_str.split('\n')
        # Filter out all the bar number lines that start with "M:".
        filtered_lines = [line for line in lines if not line.strip().startswith('M:')]
        return '\n'.join(filtered_lines)

    if isinstance(abc_full, str):
        gen_abc_list = abc_full.split("\n")
    elif isinstance(abc_full, list):
        gen_abc_list = abc_full
    else:
        gen_abc_list = abc_full

    if retain_head:
        for a in range(len(gen_abc_list)):
            if 'M:' in gen_abc_list[a]:
                abc_no_ts = remove_abc_meter(gen_abc_list[a])
                abc_no_ts += '\n'
                gen_abc_list[a] =abc_no_ts
                break
        abc_body = ""
        for abc in gen_abc_list:
            if 'L:' in abc:
                abc_body += abc.strip()
                abc_body += '\n'
            else:
                abc_body += abc.strip()
                abc_body += ' '
        return abc_body.strip()

    else:
        abc_body = ""
        for abc in gen_abc_list:
            if " | " in abc or "|]" in abc:
                abc_body += abc.strip()
        if '|]' not in abc_body:
            print("ERR! abc split is NOT body or has not |]")
            print(abc_body)
        if "%" in abc_body:
            abc_body=abc_body.replace("%1", '')
            abc_body=abc_body.replace("%2", '')
            abc_body=abc_body.replace("%3", '')
            abc_body=abc_body.replace("%4", '')
            abc_body=abc_body.replace("%5", '')
            abc_body=abc_body.replace("%6", '')
            abc_body=abc_body.replace("%7", '')
            abc_body=abc_body.replace("%8", '')
            abc_body=abc_body.replace("%9", '')
        abc_body=abc_body.strip()
        return abc_body


def randomly_make_single_note_listening_question_online_synthesis(user_name, process_idx ,input_seed, seed, q_number, question_types="audio"):
    print("Randomly making single note listening questions and online composition music")
    str_p, int_p, n_to_name = gen_pitch_list(start_p='G', start_octave=3, end_p='G', end_octave=5)
    select_keys = pseudorandom_tools.select_4_unique_keys_by_seed(n_to_name, seed=seed, selected_numbers = 4)
    select_pitches_list = []
    for key in select_keys:
        select_pitches_list.append(random.choice(n_to_name[key]))
    music_save_dir: str = f"online_sys_music_files/{user_name}/notes"
    os.makedirs(music_save_dir, exist_ok=True)
    answer,answer_index = pseudorandom_tools.select_element_by_seed(select_pitches_list, seed)

    question = copy.deepcopy(questions_template)
    question["seed"] = input_seed
    question["local_seed"] = seed
    question["task"] = "Pitch Identification"
    question["source"] = "Algorithm_for_Music_Synthesize.py"
    question["task_idx"] = q_number
    question["options"] = {"A": select_pitches_list[0], "B": select_pitches_list[1], "C": select_pitches_list[2], "D": select_pitches_list[3]}
    question["answer"] = answer_index_to_options_dict[answer_index]

    if question_types == "audio":
        audio_path = os.path.join(music_save_dir, f"note_A4_to_{answer}_bpm_60.wav")
        single_note_pitch_listening_synthesize(standard_pitch='A4', target_pitch=answer, save_dir=music_save_dir)
        question["id"] = f"Pitch Identification_synthetic_audio_{input_seed}_{q_number}_{process_idx}"
        question["question"] = "After listening to the reference pitch A4 (440 Hz), you will hear a single note. Which of the following is the correct note name?"
        question["modality"] = "audio"
        question["audio_path"] = audio_path
        question["score_path"] = None
        return question

    elif question_types == "abc":
        abc_path = os.path.join(music_save_dir, f"note_A4_to_{answer}_bpm_60.abc")
        single_note_pitch_listening_synthesize(
            standard_pitch='A4', target_pitch=answer, save_dir=music_save_dir, read_abc_question=True
        )
        try:
            gen_abc_str = read_abc_file(abc_path)
            abc_body = trim_abc_body(gen_abc_str)
            question["id"] = f"Pitch Identification_synthetic_score_{input_seed}_{q_number}_{process_idx}"
            question["question"] = f"Examine the following musical excerpt written in ABC notation and select the correct answer. Which of the following is the correct note name?\n{abc_body}"
            question["modality"] = "score"
            question["audio_path"] = None
            question["score_path"] = abc_path
            return question
        except FileNotFoundError:
            print("No such file")
        except Exception as e:
            print(e)
    else:
        print("ERR! question_types must audio or abc!")
        return None


def randomly_make_interval_listening_question_online_synthesis(user_name, process_idx, input_seed, seed, q_number, question_types="audio"):
    print("Randomly making interval listening questions and online composition music")

    random.seed(seed)

    music_save_dir: str = f"online_sys_music_files/{user_name}/interval"
    os.makedirs(music_save_dir, exist_ok=True)

    # The total range from the root note to the top note, G3 to G5, a closed interval.
    str_p_full, int_p_full, n_to_name_full_dict = gen_pitch_list(start_p='G', start_octave=3, end_p='G', end_octave=5)
    bass_to_second_pitch_list = list(n_to_name_full_dict.keys())
    # The range of root note selection is from G3 to F#5.
    str_p, int_p, n_to_name_dict = gen_pitch_list(start_p='G', start_octave=3, end_p='F#', end_octave=5)
    bass_pitch_list = list(n_to_name_dict.keys())
    interval_list = list(range(1, 13))

    # Randomly select four sets of options,
    # and it is required that the root note pitch + the number of semitones <= the highest pitch range.
    select_bass_and_interval = pseudorandom_tools.select_4_valid_pairs(
        seed,
        bass_pitch_list,
        interval_list,
        sum_min=bass_to_second_pitch_list[0],
        sum_max=bass_to_second_pitch_list[-1],
        max_attempts=1000
    )

    select_bass_name = [
        random.choice(n_to_name_dict[select_bass_and_interval[0][0]]),
        random.choice(n_to_name_dict[select_bass_and_interval[1][0]]),
        random.choice(n_to_name_dict[select_bass_and_interval[2][0]]),
        random.choice(n_to_name_dict[select_bass_and_interval[3][0]])
    ]

    select_intervals_name = [
        semitones_to_interval_name_full[select_bass_and_interval[0][1]],
        semitones_to_interval_name_full[select_bass_and_interval[1][1]],
        semitones_to_interval_name_full[select_bass_and_interval[2][1]],
        semitones_to_interval_name_full[select_bass_and_interval[3][1]]
    ]
    select_interval_name = [
        random.choice(select_intervals_name[0]),
        random.choice(select_intervals_name[1]),
        random.choice(select_intervals_name[2]),
        random.choice(select_intervals_name[3])
    ]
    music21_interval_event = [
        interval.Interval(select_interval_name[0]),
        interval.Interval(select_interval_name[1]),
        interval.Interval(select_interval_name[2]),
        interval.Interval(select_interval_name[3])
    ]

    select_second_pitches_event = [
        music21_interval_event[0].transposePitch(pitch.Pitch(select_bass_name[0])),
        music21_interval_event[1].transposePitch(pitch.Pitch(select_bass_name[1])),
        music21_interval_event[2].transposePitch(pitch.Pitch(select_bass_name[2])),
        music21_interval_event[3].transposePitch(pitch.Pitch(select_bass_name[3])),
    ]

    select_second_pitches_nameWithOctave = []
    for second_pitch in select_second_pitches_event:
        if '-' in second_pitch.nameWithOctave:
            select_second_pitches_nameWithOctave.append(second_pitch.nameWithOctave.replace('-', 'b'))
        else:
            select_second_pitches_nameWithOctave.append(second_pitch.nameWithOctave)

    option_a = select_interval_name[0]  # 'D5 - F#5 (Major Third)'
    option_b = select_interval_name[1]  # 'C#4 - A#4 (Major Sixth)'
    option_c = select_interval_name[2]  # 'A3 - G#4 (Major Seventh)'
    option_d = select_interval_name[3]  # 'E4 - E5 (Perfect Octave)'

    answer, answer_index = pseudorandom_tools.select_element_by_seed(select_bass_name, seed)

    question = copy.deepcopy(questions_template)
    question["seed"] = input_seed
    question["local_seed"] = seed
    question["task"] = "Interval Identification"
    question["source"] = "Algorithm_for_Music_Synthesize.py"
    question["task_idx"] = q_number
    question["options"] = {"A": option_a, "B": option_b, "C": option_c, "D": option_d}
    question["answer"] = answer_index_to_options_dict[answer_index]

    if question_types == "audio":
        harmonic_interval_listening_synthesize(base_pitch=answer, interval_type=select_interval_name[answer_index], save_dir=music_save_dir)
        audio_path = os.path.join(music_save_dir, f"interval_{answer}_and_{select_second_pitches_nameWithOctave[answer_index]}_{select_interval_name[answer_index]}_bpm_60.wav")
        question["id"] = f"Interval Identification_synthetic_audio_{input_seed}_{q_number}_{process_idx}"
        question["question"] = "After listening to the reference pitch A4 (440 Hz), you will hear a harmonic interval (two notes played simultaneously). Which of the following is the correct interval name?"
        question["modality"] = question_types
        question["audio_path"] = audio_path
        question["score_path"] = None
        return question

    elif question_types == "abc":
        harmonic_interval_listening_synthesize(base_pitch=answer, interval_type=select_interval_name[answer_index], save_dir=music_save_dir, read_abc_question=True)
        abc_path = os.path.join(music_save_dir, f"interval_{answer}_and_{select_second_pitches_nameWithOctave[answer_index]}_{select_interval_name[answer_index]}_bpm_60.abc")
        gen_abc_str = read_abc_file(abc_path)
        abc_body = trim_abc_body(gen_abc_str)

        question["id"] = f"Interval Identification_synthetic_score_{input_seed}_{q_number}_{process_idx}"
        question["question"] = f"Examine the following musical excerpt written in ABC notation and select the correct answer. Which of the following is the correct interval name?\n{abc_body}"
        question["modality"] = "score"
        question["audio_path"] = None
        question["score_path"] = abc_path
        return question
    else:
        return None


def randomly_make_chord_listening_question_online_synthesis(user_name, process_idx, input_seed, seed, q_number, question_types="audio"):
    print("Randomly making chord listening questions and online composition music")
    music_save_dir: str = f"online_sys_music_files/{user_name}/chord"
    os.makedirs(music_save_dir, exist_ok=True)

    loaded_chords = load_dict_from_json("static/item_content/chord.json")
    select_chord_mode_keys = pseudorandom_tools.select_4_unique_keys_by_seed(loaded_chords, seed=seed, selected_numbers = 4)
    answer, answer_index = pseudorandom_tools.select_element_by_seed(select_chord_mode_keys, seed)

    select_chord_mode_keys_list = [
        select_chord_mode_keys[0].split("_"),
        select_chord_mode_keys[1].split("_"),
        select_chord_mode_keys[2].split("_"),
        select_chord_mode_keys[3].split("_")
    ]

    complete_the_musical_note_name = {
        "C": "C3", "C#": "C#3", "Db": "Db3",
        "D": "D3", "D#": "D#3", "Eb": "Eb3",
        "E": "E3", "Fb": "Fb3", "E#": "E#3",
        "F": "F3", "F#": "F#3", "Gb": "Gb3",
        "G": "G3", "G#": "G#3", "Ab": "Ab3",
        "A": "A3", "A#": "A#3", "Bb": "Bb3",
        "B":  "B3", "Cb": "Cb3", "B#": "B#3"
    }
    chord_base_note = select_chord_mode_keys_list[answer_index][1]
    chord_base_note_full_name = complete_the_musical_note_name[chord_base_note]
    chord_style = select_chord_mode_keys_list[answer_index][2]
    chord_inversion = select_chord_mode_keys_list[answer_index][3]

    option_a = select_chord_mode_keys_list[0][1] + select_chord_mode_keys_list[0][2] + ' in ' + \
               select_chord_mode_keys_list[0][3]
    option_b = select_chord_mode_keys_list[1][1] + select_chord_mode_keys_list[1][2] + ' in ' + \
               select_chord_mode_keys_list[1][3]
    option_c = select_chord_mode_keys_list[2][1] + select_chord_mode_keys_list[2][2] + ' in ' + \
               select_chord_mode_keys_list[2][3]
    option_d = select_chord_mode_keys_list[3][1] + select_chord_mode_keys_list[3][2] + ' in ' + \
               select_chord_mode_keys_list[3][3]

    question = copy.deepcopy(questions_template)
    question["seed"] = input_seed
    question["local_seed"] = seed
    question["task"] = "Chord Identification"
    question["options"] = {"A": option_a, "B": option_b, "C": option_c, "D": option_d}
    question["answer"] = answer_index_to_options_dict[answer_index]

    if question_types == "audio":
        chord_listening_synthesize(chord_style=chord_style, chord_base_note=chord_base_note_full_name,
                                   inversion=chord_inversion, save_dir=music_save_dir)
        audio_path = os.path.join(music_save_dir, f"chord_{chord_base_note}_{chord_style}_{chord_inversion}_bpm_60.wav")

        question["id"] = f"Chord Identification_synthetic_audio_{input_seed}_{q_number}_{process_idx}"
        question["question"] = "After listening to the reference pitch A4 (440 Hz), you will hear a chord. Which of the following is the correct chord name and inversion?"
        question["modality"] = question_types
        question["source"] = "Algorithm_for_Music_Synthesize.py"
        question["task_idx"] = q_number
        question["audio_path"] = audio_path
        question["score_path"] = None
        return question

    elif question_types == "abc":
        chord_listening_synthesize(chord_style=chord_style, chord_base_note=chord_base_note_full_name,
                                   inversion=chord_inversion, save_dir=music_save_dir, read_abc_question=True)
        abc_path = os.path.join(music_save_dir, f"chord_{chord_base_note}_{chord_style}_{chord_inversion}_bpm_60.abc")
        gen_abc_str = read_abc_file(abc_path)
        abc_body = trim_abc_body(gen_abc_str)

        question["id"] = f"Chord Identification_synthetic_score_{input_seed}_{q_number}_{process_idx}"
        question["question"] = f"Examine the following musical excerpt written in ABC notation and select the correct answer. Which of the following is the correct chord name and inversion?\n{abc_body}"
        question["modality"] = "score"
        question["source"] = "Algorithm_for_Music_Synthesize.py"
        question["task_idx"] = q_number
        question["audio_path"] = None
        question["score_path"] = abc_path
        return question


def randomly_make_scale_question_online_synthesis(user_name, process_idx, input_seed, seed, q_number, question_types="audio"):
    print("Randomly making scale questions and online composition music")
    music_save_dir: str = f"online_sys_music_files/{user_name}/scale"
    os.makedirs(music_save_dir, exist_ok=True)

    select_scale_mode_keys = pseudorandom_tools.select_4_unique_keys_by_seed(scale_interval_names, seed=seed, selected_numbers = 4)
    select_tonic_name_list = pseudorandom_tools.select_4_unique_keys_by_seed(note_name_add_octave_in_reasonable, seed=seed, selected_numbers = 4)

    select_options_list_audio = [
        select_tonic_name_list[0] + " " + select_scale_mode_keys[0],
        select_tonic_name_list[1] + " " + select_scale_mode_keys[1],
        select_tonic_name_list[2] + " " + select_scale_mode_keys[2],
        select_tonic_name_list[3] + " " + select_scale_mode_keys[3]
    ]
    answer, answer_index = pseudorandom_tools.select_element_by_seed(select_options_list_audio, seed)

    question = copy.deepcopy(questions_template)
    question["seed"] = input_seed
    question["local_seed"] = seed
    question["task"] = "Tonality Identification"
    question["answer"] = answer_index_to_options_dict[answer_index]

    if question_types == "audio":
        s_t_n_l_a_i = select_tonic_name_list[answer_index]
        s_s_m_k_a_i = select_scale_mode_keys[answer_index]
        audio_path = os.path.join(music_save_dir, f"scale_{s_t_n_l_a_i}_{s_s_m_k_a_i}_bpm_60.wav")

        scale_listening_synthesize(base_pitch=select_tonic_name_list[answer_index], scale_type=select_scale_mode_keys[answer_index], save_dir=music_save_dir)

        question["id"] = f"Tonality Identification_synthetic_audio_{input_seed}_{q_number}_{process_idx}"
        question["question"] = "After listening to the reference pitch A4 (440 Hz), you will hear an ascending and descending octave scale. Which of the following is the correct tonic and mode?"
        question["modality"] = question_types
        question["source"] = "Algorithm_for_Music_Synthesize.py"
        question["options"] = {"A": select_options_list_audio[0],
                               "B": select_options_list_audio[1],
                               "C": select_options_list_audio[2],
                               "D": select_options_list_audio[3]}
        question["task_idx"] = q_number
        question["audio_path"] = audio_path
        question["score_path"] = None
        return question

    elif question_types == "abc":
        scale_listening_synthesize(base_pitch=select_tonic_name_list[answer_index], scale_type=select_scale_mode_keys[answer_index], save_dir=music_save_dir, read_abc_question=True)
        abc_path = os.path.join(music_save_dir, f"scale_{select_tonic_name_list[answer_index]}_{select_scale_mode_keys[answer_index]}_bpm_60.abc")
        gen_abc_str = read_abc_file(abc_path)
        abc_body = trim_abc_body(gen_abc_str)

        question["id"] = f"Tonality Identification_synthetic_score_{input_seed}_{q_number}_{process_idx}"
        question["question"] = f"Examine the following musical excerpt written in ABC notation and select the correct answer. Which of the following is the correct mode?\n{abc_body}"
        question["modality"] = "score"
        question["source"] = "Algorithm_for_Music_Synthesize.py"
        question["options"] = {"A": select_options_list_audio[0].split(" ")[1],
                               "B": select_options_list_audio[1].split(" ")[1],
                               "C": select_options_list_audio[2].split(" ")[1],
                               "D": select_options_list_audio[3].split(" ")[1]}
        question["task_idx"] = q_number
        question["audio_path"] = None
        question["score_path"] = abc_path
        return question


def randomly_make_rhythm_question_online_synthesis(user_name, process_idx, input_seed, seed, q_number):

    print("Randomly making rhythm questions and online composition music")
    music_save_dir: str = f"online_sys_music_files/{user_name}/rhythm"
    os.makedirs(music_save_dir, exist_ok=True)

    random.seed(seed)
    select_bpm = random.sample(list(bpm_name_to_bpm.values()), 1)
    select_ts = random.sample(["44", "68"], 1)

    select_json_file_name = f"static/item_content/rhythm_{str(select_ts[0])}_{str(select_bpm[0])}.json"

    loaded_rhythm = load_dict_from_json(select_json_file_name)

    select_rhythm_mode_keys = pseudorandom_tools.select_4_unique_keys_by_seed(
        loaded_rhythm, seed=seed,selected_numbers=4
    )


    options_test = []

    if select_ts == ['44']:
        for select_rhythm_mode_key in select_rhythm_mode_keys:
            r_list = select_rhythm_mode_key.split()
            option_str = ""
            for r in r_list[:4]:
                option_str += f"{r} "
            option_str += "| "
            for r in r_list[4:8]:
                option_str += f"{r} "
            option_str += "|] "
            options_test.append(option_str.strip())
    else:
        for select_rhythm_mode_key in select_rhythm_mode_keys:
            r_list = select_rhythm_mode_key.split()
            option_str = ""
            for r in r_list[:2]:
                option_str += f"{r} "
            option_str += "| "
            for r in r_list[2:4]:
                option_str += f"{r} "
            option_str += "|] "
            options_test.append(option_str.strip())


    answer, answer_index = pseudorandom_tools.select_element_by_seed(options_test, seed)

    ts_d = {
        "44": "4/4",
        "68": "6/8",
    }

    audio_path = rhythmic_pattern_listening_synthesize(
        rhythmic_pattern_str=answer, bpm=select_bpm[0], time_signature=ts_d[str(select_ts[0])], music_key=0, save_dir=music_save_dir
    )

    bpm_key = f'rhythm{select_ts[0]}_bpm{select_bpm[0]}'
    demo_wav = os.path.join("static/music_theory_examination/rhythm_demo", bpm_key + '.wav')
    merge_and_adjust_volume(
        input_wav1=demo_wav, input_wav2=audio_path, output_wav=audio_path, volume1=0, volume2=20
    )

    question = copy.deepcopy(questions_template)
    question["id"] = f"Rhythm Transcription_synthetic_audio_{input_seed}_{q_number}_{process_idx}"
    question["seed"] = input_seed
    question["local_seed"] = seed
    question["question"] = f"After a reference metronome click at {str(select_bpm[0])} BPM, you will hear a two-bar rhythm in {ts_d[str(select_ts[0])]} time. Which of the following is the correct rhythmic pattern?\n*(In the notation below, each `x` represents a sixteenth note. A number after `x` is a duration multiplier, e.g., `x` 2=eighth note. `(3` starts a triplet.)*"
    question["task"] = "Rhythm Transcription"
    question["modality"] = 'audio'
    question["source"] = "Algorithm_for_Music_Synthesize.py"
    question["task_idx"] = q_number
    question["options"] = {"A": options_test[0], "B": options_test[1], "C": options_test[2], "D": options_test[3]}
    question["answer"] = answer_index_to_options_dict[answer_index]
    question["audio_path"] = audio_path
    question["score_path"] = None
    return question


def save_lm_melody_dict_to_json(data, json_save_file_path):
    try:
        dir_path = os.path.dirname(json_save_file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(json_save_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"ERR - {str(e)}")
        return False


def gen_melody_and_context(process_idx, seed, music_save_dir, model, tokenizer):
    random.seed(seed)
    select_ts = random.choice(all_ts)
    output_text_dir = f"melody_generation/output_files_{process_idx}"
    os.makedirs(output_text_dir, exist_ok=True)

    # gen abc
    infer_from_loaded_model(
        seed,
        model=model,
        tokenizer=tokenizer,
        output_dir_path=output_text_dir,
        num_samples=10,
        m=select_ts,
        time_signature=all_ts_dict[select_ts]
    )

    # text to midi
    s_ts = all_ts_dict[select_ts]
    json_path = os.path.join(output_text_dir, f"generated_texts_ts_{s_ts}.json")

    # Conversion
    save_dir_content_for_melody_json = batch_gen_melody_file_and_item(
        json_path, select_number=5, seed=seed, save_path=music_save_dir
    )
    melody_json = os.path.join(music_save_dir, f"lm_melody_{all_ts_dict[select_ts]}.json")
    save_lm_melody_dict_to_json(save_dir_content_for_melody_json, melody_json)
    return melody_json


def randomly_make_time_signature_question_online_synthesis(
        user_name, process_idx, input_seed, seed, q_number, question_types="audio", model=None, tokenizer=None
):
    music_save_dir: str = f"online_sys_music_files/{user_name}/lm_gen_melody_for_ts"
    os.makedirs(music_save_dir, exist_ok=True)

    # Generate melody, including generating abc and conversion
    melody_json = gen_melody_and_context(process_idx, seed, music_save_dir, model, tokenizer)
    loaded_lm = load_dict_from_json(melody_json)
    select_answer, select_answer_idx = pseudorandom_tools.select_element_by_seed(list(loaded_lm.keys()), seed)

    select_dict = loaded_lm[select_answer]
    # select_bpm = select_dict['bpm']
    select_ts = select_dict['time signature']
    select_bar_number = select_dict['bar_number']
    select_abc_context = select_dict['bar']  # list, no bar
    select_wav_file = select_dict['wav_path']

    all_ts_copy = copy.deepcopy(all_ts)
    all_ts_copy.remove(select_ts)
    # The "remove" method must be used with caution as it directly modifies the original variable
    options = random.sample(all_ts_copy, 3)
    options.append(select_ts)
    random.shuffle(options)

    target_index = options.index(select_ts)

    question = copy.deepcopy(questions_template)
    question["seed"] = input_seed
    question["local_seed"] = seed
    question["task"] = "Meter Identification"
    question["options"] = {"A": options[0], "B": options[1], "C": options[2], "D": options[3]}
    question["answer"] = answer_index_to_options_dict[target_index]
    question["task_idx"] = q_number
    question["score_path"] = None

    if question_types == "audio":
        question["id"] = f"Meter Identification_synthetic_audio_{input_seed}_{q_number}_{process_idx}"
        question["question"] = f"You will hear a {select_bar_number}-bar melody, Which of the following is the correct time signature?"
        question["modality"] = question_types
        question["source"] = "Algorithm_for_Music_Synthesize.py"
        question["audio_path"] = select_wav_file
        return question
    elif question_types == "abc":
        abc_body = trim_abc_body(select_abc_context, retain_head=True)  # select_abc_context is a list,no bar
        question["id"] = f"Meter Identification_synthetic_score_{input_seed}_{q_number}_{process_idx}"
        question["question"] = f"Examine the following music score in ABC notation and select the correct answer. Which of the following is the correct time signature?\n{abc_body}"
        question["modality"] = "score"
        question["source"] = "Algorithm_for_Music_Synthesize.py"
        question["audio_path"] = None
        return question


def randomly_make_melody_question_online_synthesis(user_name, process_idx, input_seed, seed, q_number, model=None, tokenizer=None):
    print("Randomly making melody questions and online composition music")
    music_save_dir: str = f"online_sys_music_files/{user_name}/lm_gen_melody_for_melody"
    os.makedirs(music_save_dir, exist_ok=True)

    melody_json = gen_melody_and_context(process_idx, seed, music_save_dir,  model, tokenizer)

    loaded_lm = load_dict_from_json(melody_json)

    select_answer, select_answer_idx = pseudorandom_tools.select_element_by_seed(list(loaded_lm.keys()), seed)

    select_dict = loaded_lm[select_answer]
    select_bpm = select_dict['bpm']
    select_ts = select_dict['time signature']
    select_bar_number = select_dict['bar_number']
    select_bar_context = select_dict['bar']
    select_wav_file = select_dict['wav_path']

    select_bar_i = random.randint(1, select_bar_number)

    answer_bar = select_bar_context[select_bar_i]

    # Create interference items
    # Step 1: Eliminate the reference value and generate the candidate list
    candidates = [item for item in select_bar_context if (item != answer_bar and 'X:1' not in item)]
    # Step 2: Select 3 elements without repetition randomly from the candidate list
    options = random.sample(candidates, 3)
    # Add the correct answer
    options.append(answer_bar)
    # Shuffle
    random.shuffle(options)

    target_index = options.index(answer_bar)

    select_ts_replace = select_ts.replace('/', '')
    bpm_key = f'rhythm{select_ts_replace}_bpm{select_bpm}'

    demo_wav = os.path.join("static/music_theory_examination/rhythm_demo", bpm_key + '.wav')
    merge_and_adjust_volume(
        input_wav1=demo_wav, input_wav2=select_wav_file, output_wav=select_wav_file, volume1=0, volume2=20
    )

    question = copy.deepcopy(questions_template)
    question["id"] = f"Melody Transcription_synthetic_audio_{input_seed}_{q_number}_{process_idx}"
    question["seed"] = input_seed
    question["local_seed"] = seed
    question["question"] = f"After a reference metronome click at {str(select_bpm)} BPM, you will hear a {select_bar_number}-bar melody in {select_ts} time. Which of the following is the correct ABC notation for bar {select_bar_i} of the melody?"
    question["task"] = "Melody Transcription"
    question["modality"] = "audio"
    question["source"] = "Algorithm_for_Music_Synthesize.py"
    question["task_idx"] = q_number
    question["options"] = {"A": options[0], "B": options[1], "C": options[2], "D": options[3]}
    question["answer"] = answer_index_to_options_dict[target_index]
    question["audio_path"] = select_wav_file
    question["score_path"] = None
    return question


def randomly_make_questions_with_online_synthesis(
        num_process,
        process_idx,
        user_name,
        number_of_questions_type: int = 12,
        number_of_each_questions: int = 10,
        input_seed=100,
        model=None,
        tokenizer=None
):

    start_time = time.perf_counter()

    seeds_chain_dict, seeds = pseudorandom_tools.generate_3d_random_chain(input_seed, [number_of_questions_type, number_of_each_questions, num_process])

    test_questions = []
    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_single_note_listening_question_online_synthesis(user_name=user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[0][i][process_idx], q_number=i, question_types='audio'))

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_interval_listening_question_online_synthesis(user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[1][i][process_idx], q_number=i, question_types='audio'))

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_interval_listening_question_online_synthesis(user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[2][i][process_idx], q_number=i, question_types="abc"))

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_chord_listening_question_online_synthesis(user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[3][i][process_idx], q_number=i, question_types='audio'))

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_chord_listening_question_online_synthesis(user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[4][i][process_idx], q_number=i, question_types="abc"))

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_scale_question_online_synthesis(user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[5][i][process_idx], q_number=i, question_types='audio'))

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_scale_question_online_synthesis(user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[6][i][process_idx], q_number=i, question_types="abc"))

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_rhythm_question_online_synthesis(user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[7][i][process_idx], q_number=i))

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_time_signature_question_online_synthesis(
            user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[8][i][process_idx], q_number=i, question_types="audio", model=model, tokenizer=tokenizer
        )
    )

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_time_signature_question_online_synthesis(
            user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[9][i][process_idx], q_number=i, question_types="abc",  model=model, tokenizer=tokenizer
        )
    )

    for i in range(number_of_each_questions):
        test_questions.append(randomly_make_melody_question_online_synthesis(
            user_name, process_idx=process_idx, input_seed=input_seed, seed=seeds[10][i][process_idx], q_number=i, model=model, tokenizer=tokenizer
        )
    )

    for i in range(number_of_each_questions):
        test_questions.append(
            randomly_make_music_theory_questions(
                process_idx=process_idx,
                input_seed = input_seed,
                seed=seeds[11][i][process_idx],
                q_number=i,
                music_theory_questions_jsonl_path="static/music_theory_examination/music_theory_questions/music_theory_questions.jsonl"
            )
        )

    # Check if the file exists
    for q in test_questions:
        if q["audio_path"] is not None:
            if not os.path.exists(q["audio_path"]):
                audio_p = q["audio_path"]
                warnings.warn(f"File not found:{audio_p}")
        elif q["score_path"] is not None:
            if not os.path.exists(q["score_path"]):
                abc_p = q["score_path"]
                warnings.warn(f"File not found:{abc_p}")

    end_time = time.perf_counter()
    employ_time = end_time - start_time
    return test_questions, employ_time


if __name__ == '__main__':
    print("#######################")
    print("Welcome to the Misic Benchmark Program for synthetic music and music theory.")
    user_seed = random.randint(100, 999)

    # input_user_name = 'user_name_0330'

    # questions, use_time = randomly_make_questions_with_online_synthesis(
    #     user_name=input_user_name,
    #     number_of_questions_type=13,
    #     number_of_each_questions=2,
    #     input_seed=user_seed
    # )
    #
    # save_questions_path = 'auto_sys_questions.json'
    # with open(save_questions_path, 'w', encoding='utf-8') as f:
    #     json.dump(questions, f, ensure_ascii=False, indent=4)
