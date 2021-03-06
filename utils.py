# Ofer Sabo 201511110 Daniel Ben Itzhak  338017437
from nltk.tag.stanford import StanfordNERTagger
from collections import Counter
import pickle

st = StanfordNERTagger(
    '/Users/ofersabo/PycharmProjects/NLP_A4/stanford-ner-2018-10-16/classifiers/english.all.3class.distsim.crf.ser.gz',
    '/Users/ofersabo/PycharmProjects/NLP_A4/stanford-ner-2018-10-16/stanford-ner.jar')

down = 0
up = 1
POS_OF_START = "!!!!START!!!"
POS_OF_END = "!!!!END!!!"
set_of_tags = ['PROPN', 'PRON', 'NOUN']
Mr_Mrs = set(['Mrs.', 'Ms.'])
load_from_pickle =True
live_in = True
DEBUG_RESULT = False
person = 'PERSON'
if live_in:
    location = 'LOCATION'
    relation = "Live_In"
else:
    location = 'ORGANIZATION'
    relation = "Work_For"
DT_SET = set(["DT"])


def processed_text_to_dict(file_name):
    sentence_dict = {}
    last_line_is_blank = True
    for i, line in enumerate(open(file_name)):
        line = line.strip().replace("\t", " ").split()
        if last_line_is_blank:
            last_line_is_blank = False
            sen_num = line[-1]
            sentence_dict[sen_num] = sentence_dict.get(sen_num, list())
            this_sentence = sentence_dict[sen_num]
            continue
        elif len(line) == 0:
            last_line_is_blank = True
            continue
        elif line[0].isdigit():
            word = line[1]
            ner = line[-1]
            # if ner == "GPE" or ner == "NORP": ner = "LOCATION"
            if ner == "GPE": ner = "LOCATION"  # or ner == "NORP": ner = "LOCATION"
            if line[3] == 'POS':
                ner = 'O'
            if ner == person and len(this_sentence) > 0:
                pre_tup = this_sentence[-1]
                pre_word = pre_tup[0]
                if (pre_word == 'Mrs.' or pre_word == 'Ms.'):
                    this_sentence[-1] = (pre_word, person)

            this_sentence.append((word, ner))

    return sentence_dict


def extract_word_from_tuple(tup):
    x = tup[0]
    if " " in x:
        return x.split()[0]
    return x


def write_to_file(file_name, list_of_text):
    with open(file_name, 'w') as f:
        for s in list_of_text:
            f.write(s)


def extract_ner_inbetween_loc(ele, sen):
    inbetween = False
    if sen[int(ele[-1]) - 1][-1] == "GPE":
        inbetween = True

    return inbetween


def extract_ner_inbetween_per(ele, sen):
    inbetween_per = False
    if sen[int(ele[-1]) - 1][-1] == person:
        inbetween_per = True

    return inbetween_per


def find_joint_route(per_route, loc_route, this_sentence_proccesed_data):
    if len(per_route) > len(loc_route):
        longest = per_route
        shortest = loc_route
    else:
        longest = loc_route
        shortest = per_route

    dis = 0
    inbetween_person, inbetween_loc, had_special_prop = False, False, 0
    route_dependency = []
    route_POS = []
    for i, ele in enumerate(longest, 1):
        if ele in set(shortest):
            dis = i
            break
        if i > 1 and not inbetween_person:
            inbetween_person = extract_ner_inbetween_per(ele, this_sentence_proccesed_data)
        if i > 1 and not inbetween_loc:
            inbetween_loc = extract_ner_inbetween_loc(ele, this_sentence_proccesed_data)

        route_dependency.append(ele[1] + str(up))
        route_POS.append(this_sentence_proccesed_data[int(ele[0]) - 1][3])

    for i, ele in enumerate(shortest, 1):
        if ele in set(longest):
            dis += i
            break
        if i > 1 and not inbetween_person:
            inbetween_person = extract_ner_inbetween_per(ele, this_sentence_proccesed_data)
        if i > 1 and not inbetween_loc:
            inbetween_loc = extract_ner_inbetween_loc(ele, this_sentence_proccesed_data)

        route_dependency.append(ele[1] + str(down))
        route_POS.append(this_sentence_proccesed_data[int(ele[0]) - 1][3])

    return dis, route_dependency, route_POS, inbetween_person, inbetween_loc


def find_length_route(per, loc, route_per_word, this_sentence_proccesed_data):
    per_word = extract_word_from_tuple(per)
    loc_word = extract_word_from_tuple(loc)
    per_route = route_per_word[per_word]
    loc_route = route_per_word[loc_word]
    if len(set(per_route).intersection(set(loc_route))) == 0:
        dis = 999
        route_dependency, route_POS, inbetween_person, inbetween_loc, had_special_prop = [], [], False, False, False
    else:
        dis, route_dependency, route_POS, inbetween_person, inbetween_loc = find_joint_route(per_route, loc_route,this_sentence_proccesed_data)

    # find_father_verb(per, this_sentence_proccesed_data)
    return dis, '_'.join(route_dependency), '_'.join(route_POS), inbetween_person, inbetween_loc


def window_around_word(sentence, pos_list, index, k=2):
    exten = 0
    while index + exten < k:
        sentence.insert(0, POS_OF_START)
        pos_list.insert(0, POS_OF_START)
        exten += 1
    window = sentence[index + exten - k:index + exten]
    pos_window = pos_list[index + exten - k:index + exten]

    while index + 1 > len(sentence) - k:
        sentence.insert(len(sentence), POS_OF_END)
        pos_list.insert(len(sentence), POS_OF_END)

    window.extend(sentence[index + 1:index + k + 1])
    pos_window.extend(pos_list[index + 1:index + k + 1])

    return window, pos_window


def feature_per_word(per, this_sentence_proccesed_data, pos_list, less_detailed_than_pos):
    fe = []
    PERSON_WORD = per[0]
    length_person = len(PERSON_WORD.split())
    one_before_person = int(per[1]) - length_person
    after_person = int(per[1]) + 1
    word_index = one_before_person + 1
    lemma_form = [lemma[2] for lemma in this_sentence_proccesed_data.copy()]
    pos_list_cut = pos_list.copy()
    for i in range(1, length_person):
        del (lemma_form[word_index + 1])
        del (pos_list_cut[word_index + 1])

    assert this_sentence_proccesed_data[one_before_person + 1][1] == PERSON_WORD.split()[0]
    assert this_sentence_proccesed_data[after_person - 1][1] == PERSON_WORD.split()[-1]

    window, pos_window = window_around_word(lemma_form, pos_list_cut, word_index, 3)
    for ele in window[:int(len(window) / 2)] + pos_window:  # insert into previous words
        fe.append(ele)

    for i, pre in enumerate(window[:int(len(window) / 2)]):
        for next in window[i + 1:int(len(window) / 2)]:
            fe.append(pre + "_" + next)

    for i, pre in enumerate(window[int(len(window) / 2):]):
        for next in window[int(len(window) / 2) + i + 1:]:
            fe.append(pre + "_" + next)

    # for i,pre in enumerate(pos_window[:int(len(pos_window)/2)]):
    #     for next in pos_window[i+1:int(len(pos_window)/2)]:
    #         fe.append(pre+"_"+next)

    for i, pre in enumerate(pos_window[int(len(pos_window) / 2):]):
        for next in pos_window[int(len(pos_window) / 2) + i + 1:]:
            fe.append(pre + "_" + next)

    # pos_sequence = pos_list[:one_before_person]
    # fe.append('_'.join(pos_sequence))

    less_d = less_detailed_than_pos[:one_before_person]
    fe.append('_'.join(less_d))
    return fe, one_before_person


def extract_verbs_between_args(this_sentence_proccesed_data, per, loc, verb_list_with_index):
    PERSON_WORD = per[0]
    length_person = len(PERSON_WORD.split())
    one_before_person = int(per[1]) - length_person
    after_person = int(per[1]) + 1

    loc_word = loc[0]
    length_location = len(loc_word.split())
    one_before_location = int(loc[1]) - length_location
    after_loc = int(loc[1]) + 1
    verbs_between = []
    for v in verb_list_with_index[min(after_person, after_loc):max(one_before_person, one_before_location)]:
        if v[0] == "VERB":
            verbs_between.append(v[1])
    verbs = [this_sentence_proccesed_data[int(v) - 1][2] for v in verbs_between]
    verbs = sorted(verbs)
    return '_'.join(verbs), len(verbs)


'''
tag Dependency_connection_YES_NO DISTANCE_BETWEEN_WORDS_BY_dependency(if_not_connected_then_999)
 DISTANCE_BETWEEN_WORDS_BY_INDEX    PERSON_WORD 
 PREVIOUS_WORD_POS Two_words_before_pos one_two_words_before_pos
 NUMBER_OF_tags_BEFORE_PERSON 
  
 ###########DEPENDENCY_TO_ROOT 
 DEPENDENCY_BETWEEN_TWO_OF_THEM
 
 LOCATION_WORD PREVIOUS_WORD_POS Two_words_before_pos one_two_words_before_pos 
 NUMBER_OF_POS_BEFORE_LOCATION 
 ###########DEPENDENCY_TO_ROOT
'''


# features =  Dependency_connection_YES_NO , DISTANCE_BETWEEN_WORDS_BY_dependency, lemma form of words in a window size three, less_detailed_than_pos[:one_before_person] ,
def extract_feature(per, loc, route_to_root, ner_dict, this_sentence_proccesed_data):
    pos_list = [t[3] for t in this_sentence_proccesed_data]
    less_detailed_than_pos_with_index = [(t[4], t[0]) for t in this_sentence_proccesed_data]
    less_detailed_than_pos = [t[4] for t in this_sentence_proccesed_data]
    fe = []
    dis, route, pos_route, inbetween_person, inbetween_loc = find_length_route(per, loc,route_to_root,this_sentence_proccesed_data)
    verbs_between, len_verbs = extract_verbs_between_args(this_sentence_proccesed_data, per, loc,
                                                          less_detailed_than_pos_with_index)
    Dependency_connection_YES_NO = "Yes" if dis < 100 else "No"
    fe.append(Dependency_connection_YES_NO)
    DISTANCE_BETWEEN_WORDS_BY_dependency = dis
    fe.append(DISTANCE_BETWEEN_WORDS_BY_dependency)

    fe_per_word, one_before_per = feature_per_word(per, this_sentence_proccesed_data, pos_list, less_detailed_than_pos)

    fe.extend(fe_per_word)

    counter_smaller_than_pos = Counter(pos_list)
    for i in set_of_tags:
        fe.append(counter_smaller_than_pos[i])
    #
    fe.append(route)
    fe.append(pos_route)
    fe.append(inbetween_person)
    fe.append(inbetween_loc)

    all_verbs = sorted(
        [t[2] for t in this_sentence_proccesed_data if t[4] == "VERB"])  # item[4] for item in items if item[2]
    fe.append("_".join(all_verbs))
    #
    fe_per_word, one_before_loc = feature_per_word(loc, this_sentence_proccesed_data, pos_list, less_detailed_than_pos)

    fe.extend(fe_per_word)

    # less_between = less_detailed_than_pos[min(one_before_loc,one_before_per):max(one_before_loc,one_before_per)]
    # fe.append('_'.join(less_between))
    # counter_smaller_than_pos = Counter(less_between)
    # for i in set_of_tags:
    #     fe.append(counter_smaller_than_pos[i])

    DISTANCE_BETWEEN_WORDS_BY_INDEX = abs(one_before_loc - one_before_per)
    fe.append(DISTANCE_BETWEEN_WORDS_BY_INDEX)

    counter_smaller_than_pos = Counter(pos_list)
    for i in set_of_tags:
        fe.append(counter_smaller_than_pos[i])

    fe.append(len(ner_dict))
    fe.append(len(ner_dict))

    return fe


def get_tags_from_annotations(file_name_with_annotations="data/TRAIN.annotations"):
    sent_annotate = {}
    with open(file_name_with_annotations) as f:
        for line in f:
            line = line.split("\t")
            sen_num = line[0]
            if relation in line:
                per = line[1]
                loc = line[3]
            else:
                per = ""
                loc = ""
            sent_annotate[sen_num] = sent_annotate.get(sen_num, list())
            sent_annotate[sen_num].append((per, loc))

    return sent_annotate


def list_of_all_sentences_per_word(file_name):
    path_dict = {}  # dict of dict
    last_line_is_blank = True
    for i, line in enumerate(open(file_name)):
        line = line.strip().replace("\t", " ").split()
        if last_line_is_blank:
            last_line_is_blank = False
            sen_num = line[-1]
            path_dict[sen_num] = []
            this_sentence = path_dict[sen_num]
            continue
        elif len(line) == 0:
            last_line_is_blank = True
            continue
        elif line[0].isdigit():
            this_sentence.append(line)

    return path_dict


def get_up_word_data(sentence, current_index):
    next_data = sentence[int(sentence[current_index][5]) - 1]
    return next_data


def get_path_from_word(file_name):
    dict_to_list = list_of_all_sentences_per_word(file_name)
    mega_dict = {}
    for sen in dict_to_list:
        mega_dict[sen] = {}
        this_sen = mega_dict[sen]
        sentence = dict_to_list[sen]
        for w_list in sentence:
            original_word = w_list[1]
            index = w_list[0]
            word = original_word

            con = w_list[6]
            next_index = int(w_list[5])
            route_to_root = []
            while con != 'ROOT':
                route_to_root.append((next_index, con, word, index))
                word = sentence[next_index - 1][1]
                index = sentence[next_index - 1][0]
                con = sentence[next_index - 1][6]
                next_index = int(sentence[next_index - 1][5])

            this_sen[original_word] = route_to_root

    return mega_dict, dict_to_list


def stanford_extract_ner_from_sen(sen):
    r = st.tag(sen)
    return r


def combine_two_sentences(first, second, this_sentence_proccesed_data):
    assert len(first) == len(second)
    for i in range(len(first)):
        first_tuple = first[i]
        second_tuple = second[i]
        assert first_tuple[0] == second_tuple[0]
        if first_tuple[1] != second_tuple[1]:
            if first_tuple[1] == 'O':
                first[i] = second[i]
            if first[i][1] == "ORG":  # <class 'tuple'>: ('Justice Department', 'ORGANIZATION', 29)
                first[i] = (first[i][0], "ORGANIZATION")
        if first_tuple[1] == person and i > 0 and first[i - 1][0] in Mr_Mrs:
            first[i - 1] = (first[i - 1][0], person)
        if first_tuple[1] == location and i > 0 and this_sentence_proccesed_data[i - 1][3] in DT_SET:
            first[i - 1] = (first[i - 1][0], 'O')

        # if first_tuple[1] == location and i < len(first) -1 and this_sentence_proccesed_data[i + 1][4] == "NOUN":
        #     first[i + 1] = (first[i + 1][0],location)

    return first


def extract_ner(sen):
    all_ner = []
    i = 0
    while i < len(sen):
        if sen[i][1] != 'O':
            j = i + 1
            while j < len(sen) and sen[j][1] == sen[i][1]:
                j += 1
            ner = " ".join([sen[k][0] for k in range(i, j)])
            ner_tag = sen[i][1]
            i = j - 1
            all_ner.append((ner, ner_tag, i))
        i += 1
    return all_ner


def check_person_and_location(all_ner):
    dict_ner = {}
    for ele in all_ner:
        if ele[1] == person:
            dict_ner[person] = dict_ner.get(person, list())
            dict_ner[person].append((ele[0], ele[2]))
        elif ele[1] == location:
            dict_ner[location] = dict_ner.get(location, list())
            dict_ner[location].append((ele[0], ele[2]))

    return dict_ner


def unique_person_and_location(persons, locations):
    #from collections import Counter()
    per_dict = dict()
    for p in persons:
        per_dict[p[0]] =  per_dict.get(p[0],[])
        per_dict[p[0]].append(p[1])


    loc_dict = dict()
    for l in locations:
        loc_dict[l[0]]  = loc_dict.get(l[0],[])
        loc_dict[l[0]].append(l[1])


    return per_dict, loc_dict


def tupple_in_annotion(person, location, ann):
    tup = (person[0], location[0])
    if tup in ann:
        return 1
    return 0


def convert_to_text_only_feature(feature):
    st = ""
    for i, fe in enumerate(feature):
        st += " feature_number_" + str(i) + "=" + str(fe)
    return st


def convert_to_text(tag, feature):
    st = str(tag)
    st += convert_to_text_only_feature(feature)
    return st + "\n"


def save_to_file(var, file_name):
    with open(file_name, 'wb') as handle:
        pickle.dump(var, handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_from_file(file_name):
    with open(file_name, 'rb') as f:
        var = pickle.load(f)
    return var


def create_nereast_tupple(per_name,person_indeces,location_name,location_indences):
    min_distance = 999
    for per_index in person_indeces:
        for loc_index in location_indences:
            if abs(per_index-loc_index) < min_distance:
                min_distance = abs(per_index-loc_index)
                keep_per = per_index
                keep_loc = loc_index
    return (per_name,person_indeces[0]),(location_name,location_indences[0])