import re
import logging
import functools

from datapackage_pipelines.wrapper import ingest, spew

BAD_CHARACTERS = "'`()-"


class MKIndividualsFinder:
    def __init__(self, individuals_list):
        self.individuals_list = individuals_list
        self._normalize_names()

    @functools.lru_cache()
    def find_member(self, full_name, knesset_num):
        return self._search_for_member_with_strategy(full_name, knesset_num) or \
            self._search_for_member_with_strategy(full_name, knesset_num, reverse_name_order=True) or \
            self._search_for_member_with_strategy(full_name, knesset_num, remove_bad_characters=True) or \
            self._search_for_member_with_strategy(full_name, knesset_num, reverse_name_order=True, remove_bad_characters=True) or \
            self._search_for_member_with_strategy(full_name, knesset_num, remove_name_in_braces=True) or \
            self._search_for_member_with_strategy(full_name, knesset_num, replace_dash_with_space=True) or \
            self._search_for_member_with_strategy(full_name, knesset_num, replace_dash_with_space=True, reverse_name_order=True) or \
            self._search_for_member_with_strategy(full_name, knesset_num, replace_dash_with_space=True, remove_bad_characters=True) or \
            self._search_for_member_with_strategy(full_name, knesset_num, replace_dash_with_space=True, reverse_name_order=True, remove_bad_characters=True)

    def _search_for_member_with_strategy(self, full_name, knesset_num,
                                         remove_bad_characters=False, reverse_name_order=False,
                                         remove_name_in_braces=False, replace_dash_with_space=False):
        first_name_field = 'mk_individual_first_name'
        last_name_field = 'mk_individual_name'
        if replace_dash_with_space:
            first_name_field += '_replace_dash_with_space'
            last_name_field += '_replace_dash_with_space'
            full_name = full_name.replace("-", " ").strip()
        if remove_bad_characters:
            first_name_field += '_naked'
            last_name_field += '_naked'
            full_name = " ".join(remove_characters(full_name, BAD_CHARACTERS).split())
        if remove_name_in_braces:
            first_name_field += '_no_braced_name'
            last_name_field += '_no_braced_name'
            full_name = " ".join(re.sub(r"\(.*\)", "", full_name).strip().split())

        if reverse_name_order:
            first_name_field, last_name_field = last_name_field, first_name_field

        matches = [individual for individual in self.individuals_list
                   if "{first} {last}".format(first=individual[first_name_field],
                                              last=individual[last_name_field]) == full_name
                   and knesset_num in (position['KnessetNum'] for position in individual['positions'])]

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            logging.debug("reversed name found more than 1 matches: %s", [x['mk_individual_id'] for x in matches])

    def _normalize_names(self):
        for individual in self.individuals_list:
            for field in ['mk_individual_name', 'mk_individual_name_eng', 'mk_individual_first_name', 'mk_individual_first_name_eng']:
                if individual[field]:
                    individual[field] = individual[field].strip()
                    individual[field+"_naked"] = remove_characters(individual[field].strip(), BAD_CHARACTERS).strip()
                    individual[field + "_no_braced_name"] = re.sub(r"\(.*\)", "", individual[field]).strip()
                    individual[field + '_replace_dash_with_space'] = individual[field].replace("-", " ").strip()
                    individual[field + "_replace_dash_with_space_naked"] = remove_characters(
                        individual[field].replace("-", " ").strip(), BAD_CHARACTERS).strip()

def get_resource(votes, mk_individuals, stats):
    individuals_finder = MKIndividualsFinder(mk_individuals)
    for vote in votes:
        voter_full_name = vote['kmmbr_name'].strip()
        voter_knesset_num = vote['knesset_num']

        member = individuals_finder.find_member(voter_full_name, voter_knesset_num)

        if member:
            vote["mk_individual_id"] = member['mk_individual_id']
        else:
            vote["mk_individual_id"] = None
        yield vote
        stats["total votes"] += 1


def _get_resource_from_datapackage(datapackage, resources, resource_name):
    resource_index = next(index for index, resource in enumerate(datapackage['resources']) if resource['name'] == resource_name)
    return resources[resource_index]


def remove_characters(st, characters_to_remove):
    result = st
    for char in characters_to_remove:
        result = result.replace(char, "")
    return result


def main():
    parameters, datapackage, resources = ingest()
    resources = list(resources)
    stats = {}

    mk_individuals = _get_resource_from_datapackage(datapackage, resources, 'mk_individual')
    votes = _get_resource_from_datapackage(datapackage, resources, 'vote_rslts_kmmbr_shadow')

    mk_individuals = list(mk_individuals)

    stats["total votes"] = 0
    datapackage["resources"][1]["schema"]["fields"].append({"name": "mk_individual_id", "type": "integer"})

    spew(datapackage, [mk_individuals, get_resource(votes, mk_individuals, stats)], stats)


if __name__ == '__main__':
    main()
