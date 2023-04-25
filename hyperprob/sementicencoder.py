import copy
import itertools

from lark import Tree, Token
# from z3 import And, Bool, Real, Int, Not, Or, Xor, RealVal, Implies

from cvc5.pythonic import *

def extendWithoutDuplicates(list1, list2):
    result = []
    if list1 is not None:
        result.extend(list1)
    if list2 is not None:
        result.extend(x for x in list2 if x not in result)
    return result


class SemanticsEncoder:

    def __init__(self, model, solver,
                 list_of_subformula,
                 dictOfReals, dictOfBools, dictOfInts,
                 no_of_subformula, no_of_state_quantifier, no_of_stutter_quantifier,
                 lengthOfStutter, stutter_state_mapping, dict_pair_index):
        self.model = model
        self.solver = solver  # todo not needed here anymore
        self.list_of_subformula = list_of_subformula
        self.dictOfReals = dictOfReals
        self.dictOfBools = dictOfBools
        self.dictOfInts = dictOfInts
        self.no_of_subformula = no_of_subformula
        self.no_of_state_quantifier = no_of_state_quantifier
        self.no_of_stutter_quantifier = no_of_stutter_quantifier
        self.stutterLength = lengthOfStutter  # default value 1 (= no stutter)
        self.stutter_state_mapping = stutter_state_mapping
        self.dict_pair_index = dict_pair_index

    def genRelStutterscheds(self, stutter_scheds, rel_quant_stu):
        rel_stutter_scheds = []
        for i in range(len(stutter_scheds)):
            if i + 1 in rel_quant_stu:
                rel_stutter_scheds.append(stutter_scheds[i])
            else:
                rel_stutter_scheds.append(tuple([0 for _ in stutter_scheds[i]]))
        return tuple(rel_stutter_scheds)

    def encodeSemantics(self, hyperproperty, stutter_scheds, prev_relevant_quantifier=[]):
        # TODO check whether to remove prev_relevant_quantifier as its not used anmyore?
        relevant_quantifier = []
        relevant_quantifier_stu = []
        encoding = []

        if len(prev_relevant_quantifier) > 0:
            relevant_quantifier.extend(prev_relevant_quantifier)

        if hyperproperty.data == 'true':
            index_of_phi = self.list_of_subformula.index(hyperproperty)
            name = "holds"
            r_state = [(0, 0) for _ in range(self.no_of_stutter_quantifier)]
            rel_stutter_scheds = tuple([tuple([0 for _ in x]) for x in stutter_scheds])
            for ind in r_state:
                name += "_" + str(ind)
            name += "_" + str(index_of_phi) + "_" + str(rel_stutter_scheds)
            self.addToVariableList(name)
            encoding.append(self.dictOfBools[name])
            self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'atomic_proposition':
            ap_name = hyperproperty.children[0].children[0].value  # gets the name of the proposition
            proposition_relevant_stutter = int(
                hyperproperty.children[1].children[0].value[1])  # relevant stutter quantifier
            # TODO find relevant state
            # proposition_relevant_state = self.stutter_state_mapping[proposition_relevant_stutter-1]
            labeling = self.model.parsed_model.labeling
            if proposition_relevant_stutter not in relevant_quantifier:
                relevant_quantifier.append(proposition_relevant_stutter)
            and_for_yes = set()
            and_for_no = set()
            list_of_state_with_ap = []

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            for state in self.model.getListOfStates():
                if ap_name in labeling.get_labels_of_state(state):
                    list_of_state_with_ap.append(state)
            combined_state_list = self.generateComposedStatesWithStutter(
                relevant_quantifier)  # tuples without stutterlength

            rel_stutter_scheds = tuple([tuple([0 for _ in x]) for x in stutter_scheds])

            for r_state in combined_state_list:
                name = 'holds'
                for tup in r_state:
                    name += "_" + str(tup)
                name += "_" + str(index_of_phi) + "_" + str(rel_stutter_scheds)
                self.addToVariableList(name)  # should look like: holds_(0, 0)_(0, 0)_2_((0,0,0,0,0,0),(0,0,0,0,0,0))

                # check whether atomic proposition holds or not
                if r_state[proposition_relevant_stutter - 1][0] in list_of_state_with_ap:
                    and_for_yes.add(self.dictOfBools[name])
                else:
                    and_for_no.add(Not(self.dictOfBools[name]))
            encoding.append(And(And(list(and_for_yes)), And(list(and_for_no))))
            self.no_of_subformula += 3
            and_for_yes.clear()
            and_for_no.clear()
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'and':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                first_and = And(self.dictOfBools[name1],
                                self.dictOfBools[name2],
                                self.dictOfBools[name3])
                self.no_of_subformula += 1
                second_and = And(Not(self.dictOfBools[name1]),
                                 Or(Not(self.dictOfBools[name2]),
                                    Not(self.dictOfBools[name3])))
                self.no_of_subformula += 1
                encoding.append(Or(first_and, second_and))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'or':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                first_and = And(self.dictOfBools[name1],
                                Or(self.dictOfBools[name2],
                                   self.dictOfBools[name3]))
                self.no_of_subformula += 1
                second_and = And(Not(self.dictOfBools[name1]),
                                 And(Not(self.dictOfBools[name2]),
                                     Not(self.dictOfBools[name3])))
                self.no_of_subformula += 1
                encoding.append(Or(first_and, second_and))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'implies':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                first_and = And(self.dictOfBools[name1],
                                Or(Not(self.dictOfBools[name2]),
                                   self.dictOfBools[name3]))
                self.no_of_subformula += 1
                second_and = And(Not(self.dictOfBools[name1]),
                                 And(self.dictOfBools[name2],
                                     Not(self.dictOfBools[name3])))
                self.no_of_subformula += 1
                encoding.append(Or(first_and, second_and))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'biconditional':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                first_and = And(self.dictOfBools[name1],
                                Or(
                                    And(self.dictOfBools[name2],
                                        self.dictOfBools[name3]),
                                    And(Not(self.dictOfBools[name2]),
                                        Not(self.dictOfBools[name3]))))
                self.no_of_subformula += 1
                second_and = And(Not(self.dictOfBools[name1]),
                                 Or(
                                     And(Not(self.dictOfBools[name2]),
                                         self.dictOfBools[name3]),
                                     And(self.dictOfBools[name2],
                                         Not(self.dictOfBools[name3]))))
                self.no_of_subformula += 1
                encoding.append(Or(first_and, second_and))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'not':
            rel_quant, rel_quant_stu, encoding = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant)
            # todo extending unnecessary here, relevant_quantifier is [] anyways
            relevant_quantifier_stu = rel_quant_stu

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])

            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'holds'
                for ind in r_state:
                    name2 += "_" + str(ind)
                name2 += "_" + str(index_of_phi1) + "_"
                name2 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name2)
                encoding.append(Xor(self.dictOfBools[name1],
                                    self.dictOfBools[name2]))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'probability':
            child = hyperproperty.children[0]
            if child.data == 'next':
                rel_quant, relevant_quantifier_stu, encoding = self.encodeNextSemantics(hyperproperty,
                                                                                        stutter_scheds,
                                                                                        relevant_quantifier)
                relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant)

            elif child.data == 'until_unbounded':
                rel_quant, relevant_quantifier_stu, encoding = self.encodeUnboundedUntilSemantics(hyperproperty,
                                                                                                  stutter_scheds,
                                                                                                  relevant_quantifier)
                relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant)

            elif child.data == 'until_bounded':
                rel_quant, _, _, relevant_quantifier_stu, _, _, encoding = self.encodeBoundedUntilSemantics(
                    hyperproperty, stutter_scheds, relevant_quantifier)
                relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant)

            elif child.data == 'future':
                rel_quant, relevant_quantifier_stu, encoding = self.encodeFutureSemantics(hyperproperty,
                                                                                          stutter_scheds,
                                                                                          relevant_quantifier)
                relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant)

            elif child.data == 'global':
                rel_quant, relevant_quantifier_stu, encoding = self.encodeGlobalSemantics(hyperproperty,
                                                                                          stutter_scheds,
                                                                                          relevant_quantifier)
                relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant)

            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'less_probability':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                and_eq = And(self.dictOfBools[name1],
                             self.dictOfReals[name2] < self.dictOfReals[name3])
                self.no_of_subformula += 1
                and_not_eq = And(Not(self.dictOfBools[name1]),
                                 self.dictOfReals[name2] >= self.dictOfReals[name3])
                self.no_of_subformula += 1
                encoding.append(Or(and_eq, and_not_eq))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'equal_probability':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                and_eq = And(self.dictOfBools[name1],
                             self.dictOfReals[name2] == self.dictOfReals[name3])
                self.no_of_subformula += 1
                and_not_eq = And(Not(self.dictOfBools[name1]),
                                 self.dictOfReals[name2] != self.dictOfReals[name3])
                self.no_of_subformula += 1
                encoding.append(Or(and_eq, and_not_eq))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'greater_probability':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                and_eq = And(self.dictOfBools[name1],
                             self.dictOfReals[name2] > self.dictOfReals[name3])
                self.no_of_subformula += 1
                and_not_eq = And(Not(self.dictOfBools[name1]),
                                 self.dictOfReals[name2] <= self.dictOfReals[name3])
                self.no_of_subformula += 1
                encoding.append(Or(and_eq, and_not_eq))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'greater_and_equal_probability':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                and_eq = And(self.dictOfBools[name1],
                             self.dictOfReals[name2] >= self.dictOfReals[name3])
                self.no_of_subformula += 1
                and_not_eq = And(Not(self.dictOfBools[name1]),
                                 self.dictOfReals[name2] < self.dictOfReals[name3])
                self.no_of_subformula += 1
                encoding.append(Or(and_eq, and_not_eq))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'less_and_equal_probability':
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_of_phi1 = self.list_of_subformula.index(hyperproperty.children[0])
            index_of_phi2 = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'holds'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi1) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_of_phi2) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                and_eq = And(self.dictOfBools[name1],
                             self.dictOfReals[name2] <= self.dictOfReals[name3])
                self.no_of_subformula += 1
                and_not_eq = And(Not(self.dictOfBools[name1]),
                                 self.dictOfReals[name2] > self.dictOfReals[name3])
                self.no_of_subformula += 1
                encoding.append(Or(and_eq, and_not_eq))
                self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data == 'constant_probability':
            #constant = RealVal(hyperproperty.children[0].value).limit_denominator(10000)
            constant = RealVal(hyperproperty.children[0].value)
            #constant = hyperproperty.children[0].value # str, also seems to work??
            index_of_phi = self.list_of_subformula.index(hyperproperty)
            name = "prob"
            r_state = [(0, 0) for _ in range(self.no_of_stutter_quantifier)]
            rel_stutter_scheds = tuple([tuple([0 for _ in x]) for x in stutter_scheds])
            for tup in r_state:
                name += "_" + str(tup)
            name += "_" + str(index_of_phi) + "_" + str(rel_stutter_scheds)
            self.addToVariableList(name)
            encoding.append(self.dictOfReals[name] == constant)
            self.no_of_subformula += 1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        elif hyperproperty.data in ['add_probability', 'subtract_probability', 'multiply_probability']:
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(hyperproperty.children[0], stutter_scheds)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(hyperproperty.children[1], stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(rel_quant1, rel_quant2)
            relevant_quantifier_stu = extendWithoutDuplicates(rel_quant_stu1, rel_quant_stu2)
            encoding = enc1 + enc2

            index_of_phi = self.list_of_subformula.index(hyperproperty)
            index_left = self.list_of_subformula.index(hyperproperty.children[0])
            index_right = self.list_of_subformula.index(hyperproperty.children[1])
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
            for r_state in combined_state_list:
                name1 = 'prob'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_"
                name1 += str(self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu))
                self.addToVariableList(name1)
                name2 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_left) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu1))
                self.addToVariableList(name2)
                name3 = 'prob'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name3 += "_" + str(r_state[ind])
                    else:
                        name3 += "_" + str((0, 0))
                name3 += "_" + str(index_right) + "_" + str(self.genRelStutterscheds(stutter_scheds, rel_quant_stu2))
                self.addToVariableList(name3)
                if hyperproperty.data == 'add_probability':
                    encoding.append(self.dictOfReals[name1] == (
                            self.dictOfReals[name2] + self.dictOfReals[name3]))
                    self.no_of_subformula += 2
                elif hyperproperty.data == 'subtract_probability':
                    encoding.append(self.dictOfReals[name1] == (
                            self.dictOfReals[name2] - self.dictOfReals[name3]))
                    self.no_of_subformula += 2
                elif hyperproperty.data == 'multiply_probability':
                    encoding.append(self.dictOfReals[name1] == (
                            self.dictOfReals[name2] * self.dictOfReals[name3]))
                    self.no_of_subformula += 2
                else:
                    print("Unexpected operator. Exiting")
                    return -1
            return relevant_quantifier, relevant_quantifier_stu, encoding

        else:  # todo when is this case used, should never occur?
            rel_quant, relevant_quantifier_stu, encoding = self.encodeSemantics(hyperproperty.children[0],
                                                                                stutter_scheds)
            return rel_quant, relevant_quantifier_stu, encoding

    def addToVariableList(self, name):
        # TODO reuse method in modelchecker
        if name[0] == 'h' and not name.startswith('holdsToInt'):  # and name not in self.dictOfBools.keys():
            self.dictOfBools[name] = Bool(name)
        elif (name[0] in ['p', 'd', 'r'] or name.startswith('holdsToInt')):  # and name not in self.dictOfReals.keys():
            self.dictOfReals[name] = Real(name)
        elif name[0] in ['a', 't']:
            self.dictOfInts[name] = Int(name)

    def generateComposedStatesWithStutter(self, list_of_relevant_quantifier):
        """
        Generates combination of states based on relevant quantifiers
        :param list_of_relevant_quantifier: ranges from value 1- (no. of quantifiers)
        :return: list of composed states.
        """
        states_with_stuttering = list(
            itertools.product(self.model.getListOfStates(), list(range(self.stutterLength))))

        stored_list = []
        for quant in range(1, self.no_of_state_quantifier + 1):
            if quant in list_of_relevant_quantifier:
                stored_list.append(states_with_stuttering)
            else:
                stored_list.append([(0, 0)])
        return list(itertools.product(*stored_list))

    def generateComposedStates(self, list_of_relevant_quantifier):
        """
        Generates combination of states based on relevant quantifiers
        :param list_of_relevant_quantifier: ranges from value 1- (no. of quantifiers)
        :return: list of composed states.
        """
        stored_list = []
        for quant in range(1, self.no_of_state_quantifier + 1):
            if quant in list_of_relevant_quantifier:
                stored_list.append(self.model.getListOfStates())
            else:
                stored_list.append([0])
        return list(itertools.product(*stored_list))

    def genSuccessors(self, r_state, ca, stutter_scheds, relevant_quantifier):
        """
        Generates successor states of r_state under a given choice of actions and a stutter-quantifier, wrt rel quants
        :param r_state: tuple of states, one for each state quantifier
        :param ca: list of chosen actions, one for each state corresponding to a relevant quantifier
        :param stutter_scheds: tuple of stutter-schedulers, one for each stutter quantifier
        :param relevant_quantifier: list of relevant quantifiers (referenced by name)
        :return: list of successor states with entries of the form ["successor state", "probability of reaching that state"]
        """
        dicts = []
        for l in range(len(relevant_quantifier)):
            rel_quant_index = relevant_quantifier[l] - 1
            rel_state = r_state[rel_quant_index]
            if stutter_scheds[rel_quant_index][self.dict_pair_index[rel_state[0], ca[l]]] <= rel_state[1]:
                succ = (self.model.dict_of_acts_tran[str(rel_state[0]) + " " + str(ca[l])])
                list_of_all_succ = []
                for s in succ:
                    space = s.find(' ')
                    succ_state = (int(s[0:space]), 0)
                    list_of_all_succ.append([str(succ_state), s[space + 1:]])
            else:  # i.e., if stutter_scheds[rel_quant_index][self.dict_pair_index[rel_state[0], ca[l]]] > rel_state[1]
                list_of_all_succ = [[str((rel_state[0],
                                          rel_state[1] + 1)),
                                     str(1)]]
            dicts.append(list_of_all_succ)
        return list(itertools.product(*dicts))

    def encodeNextSemantics(self, hyperproperty, stutter_scheds, prev_relevant_quantifier=[]):
        phi1 = hyperproperty.children[0].children[0]
        index_of_phi1 = self.list_of_subformula.index(phi1)
        index_of_phi = self.list_of_subformula.index(hyperproperty)
        relevant_quantifier, rel_quant_stu1, encoding = self.encodeSemantics(phi1,
                                                                             stutter_scheds,
                                                                             prev_relevant_quantifier)

        combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)
        # todo think: only consider those states that are actually reachable under the current stutter-scheduler??
        # e.g. for the trivial stuttering we can only reach states (s,0), not (s,1)

        # relevant quantifiers for temporal operators are all the quantifiers occuring in the subformulas
        relevant_quantifier_stu = copy.deepcopy(relevant_quantifier)
        stutter_scheds1 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu1)
        stutter_scheds0 = self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu)

        for r_state in combined_state_list:
            # encode relationship between holds and holdsToInt
            holds1 = 'holds'
            str_r_state = ""
            for tup in r_state:
                str_r_state += "_" + str(tup)
            holds1 += str_r_state + "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
            self.addToVariableList(holds1)
            holdsToInt1 = 'holdsToInt' + str_r_state + "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
            self.addToVariableList(holdsToInt1)
            prob_phi = 'prob' + str_r_state + "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
            self.addToVariableList(prob_phi)
            first_and = Or(
                And(self.dictOfReals[holdsToInt1] == RealVal(1),
                    self.dictOfBools[holds1]),
                And(self.dictOfReals[holdsToInt1] == RealVal(0),
                    Not(self.dictOfBools[holds1])))
            self.no_of_subformula += 3
            encoding.append(first_and)

            # create list of all possible actions for r_state
            dicts_act = []
            for l in range(len(relevant_quantifier)):
                dicts_act.append(self.model.dict_of_acts[r_state[relevant_quantifier[l] - 1][0]])
            combined_acts = list(itertools.product(*dicts_act))

            # calculate probability of Next phi1
            sum_of_probs = RealVal(0)
            for ca in combined_acts:
                # create list of successors of r_state with probabilities under currently considered stuttering and actions
                # list entries are tuples (l_1, ... l_n) where l_i = (s, p) where
                # s is a successor of the ith relevant state (i.e. r_state[relevant_quantifier[i]][0] )
                # p is the transition probability (1 if the transition is a stutter step)
                combined_succ = self.genSuccessors(r_state, ca, stutter_scheds0, relevant_quantifier)

                # calculate probability based on probabilities that phi1 holds in the successor states
                for cs in combined_succ:
                    holdsToInt_succ = 'holdsToInt'
                    product = RealVal(1)

                    for l in range(1, self.no_of_stutter_quantifier + 1):
                        if l in relevant_quantifier:
                            l_index = relevant_quantifier.index(l)
                            succ_state = cs[l_index][0]
                            holdsToInt_succ += "_" + succ_state
                            product *= RealVal(cs[l_index][1])
                            product *= self.dictOfReals["a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                        else:
                            holdsToInt_succ += "_" + str((0, 0))

                    holdsToInt_succ += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
                    self.addToVariableList(holdsToInt_succ)
                    product *= self.dictOfReals[holdsToInt_succ]

                    sum_of_probs += product
                    self.no_of_subformula += 1

            prob_calc_enc = self.dictOfReals[prob_phi] == sum_of_probs
            self.no_of_subformula += 1
            encoding.append(prob_calc_enc)

        return relevant_quantifier, relevant_quantifier_stu, encoding

    def encodeUnboundedUntilSemantics(self, hyperproperty, stutter_scheds, relevant_quantifier=[]):
        index_of_phi = self.list_of_subformula.index(hyperproperty)
        phi1 = hyperproperty.children[0].children[0]
        index_of_phi1 = self.list_of_subformula.index(phi1)
        rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(phi1, stutter_scheds)
        relevant_quantifier = extendWithoutDuplicates(rel_quant1, relevant_quantifier)
        phi2 = hyperproperty.children[0].children[1]
        index_of_phi2 = self.list_of_subformula.index(phi2)
        rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(phi2, stutter_scheds)

        relevant_quantifier = extendWithoutDuplicates(rel_quant2, relevant_quantifier)
        combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)

        relevant_quantifier_stu = copy.deepcopy(relevant_quantifier)
        stutter_scheds0 = self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu)
        stutter_scheds1 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu1)
        stutter_scheds2 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu2)

        encoding = enc1 + enc2

        for r_state in combined_state_list:
            # encode cases where we know probability is 0 or 1 and require probs variables to be in [0,1]
            holds1 = 'holds'
            for ind in range(0, len(r_state)):
                if (ind + 1) in rel_quant1:
                    holds1 += "_" + str(r_state[ind])
                else:
                    holds1 += "_" + str((0, 0))
            holds1 += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
            self.addToVariableList(holds1)
            holds2 = 'holds'
            for ind in range(0, len(r_state)):
                if (ind + 1) in rel_quant2:
                    holds2 += "_" + str(r_state[ind])
                else:
                    holds2 += "_" + str((0, 0))
            holds2 += "_" + str(index_of_phi2) + "_" + str(stutter_scheds2)
            self.addToVariableList(holds2)
            prob_phi = 'prob'
            for tup in r_state:
                prob_phi += "_" + str(tup)
            prob_phi += "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
            self.addToVariableList(prob_phi)

            #new_prob_const_0 = self.dictOfReals[prob_phi] >= float(0)
            #new_prob_const_1 = self.dictOfReals[prob_phi] <= float(1)

            first_implies = And(Implies(self.dictOfBools[holds2],
                                        self.dictOfReals[prob_phi] == RealVal(1)),
                                Implies(And(Not(self.dictOfBools[holds1]),
                                            Not(self.dictOfBools[holds2])),
                                        self.dictOfReals[prob_phi] == RealVal(0))
                                )
            encoding.append(first_implies)
            self.no_of_subformula += 4

            # create list of all possible actions for r_state
            dicts_act = []
            for l in range(len(relevant_quantifier)):
                dicts_act.append(self.model.dict_of_acts[r_state[relevant_quantifier[l] - 1][0]])
            combined_acts = list(itertools.product(*dicts_act))

            # precondition for probability calculation: probability isnt 0 or 1
            implies_precedent = And(self.dictOfBools[holds1], Not(self.dictOfBools[holds2]))
            self.no_of_subformula += 2

            # encode probability calculation
            sum_of_probs = RealVal(0)
            loop_condition_list = []
            for ca in combined_acts:
                # create list of successors of r_state with probabilities under currently considered stuttering and actions
                combined_succ = self.genSuccessors(r_state, ca, stutter_scheds0, relevant_quantifier)

                # create equation system for probabilities and a loop condition to ensure correctness
                for cs in combined_succ:
                    prob_succ = 'prob'
                    holds_succ = 'holds'
                    d_current = 'd'
                    d_succ = 'd'
                    product = RealVal(1)
                    sched_prob = RealVal(1)

                    for l in range(1, self.no_of_state_quantifier + 1):
                        if l in relevant_quantifier:
                            l_index = relevant_quantifier.index(l)
                            succ_state = cs[l_index][0]
                            prob_succ += "_" + succ_state
                            holds_succ += "_" + succ_state
                            d_succ += "_" + succ_state
                            product *= RealVal(cs[l_index][1])
                            product *= self.dictOfReals["a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                            sched_prob *= self.dictOfReals["a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                        else:
                            prob_succ += "_" + str((0, 0))
                            holds_succ += "_" + str((0, 0))
                            d_succ += "_" + str((0, 0))
                        d_current += "_" + str(r_state[l - 1])

                    prob_succ += "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
                    self.addToVariableList(prob_succ)
                    product *= self.dictOfReals[prob_succ]
                    sum_of_probs += product
                    self.no_of_subformula += 1

                    # loop condition
                    holds_succ += "_" + str(index_of_phi2) + "_" + str(stutter_scheds2)
                    self.addToVariableList(holds_succ)
                    d_current += "_" + str(index_of_phi2) + "_" + str(stutter_scheds2)
                    self.addToVariableList(d_current)
                    d_succ += "_" + str(index_of_phi2) + "_" + str(stutter_scheds2)
                    self.addToVariableList(d_succ)
                    loop_condition_list.append(And(sched_prob > RealVal(0),
                                                   Or(self.dictOfBools[holds_succ],
                                                      self.dictOfReals[d_current] > self.dictOfReals[d_succ])
                                                   ))
                    self.no_of_subformula += 3

            prob_calc_enc = self.dictOfReals[prob_phi] == sum_of_probs
            self.no_of_subformula += 1
            if len(loop_condition_list) == 1:
                loop_condition_post = loop_condition_list[0]
            else:
                loop_condition_post = Or(loop_condition_list)
            loop_condition = Implies(self.dictOfReals[prob_phi] > RealVal(0),
                                     loop_condition_post)
            self.no_of_subformula += 2
            implies_antecedent = And(prob_calc_enc, loop_condition)
            self.no_of_subformula += 1
            encoding.append(Implies(implies_precedent, implies_antecedent))
            self.no_of_subformula += 1

        return relevant_quantifier, relevant_quantifier_stu, encoding

    def encodeBoundedUntilSemantics(self, hyperproperty, stutter_scheds, relevant_quantifier=[]):
        k1 = int(hyperproperty.children[0].children[1].value)
        k2 = int(hyperproperty.children[0].children[2].value)

        index_of_phi = self.list_of_subformula.index(hyperproperty)
        phi1 = hyperproperty.children[0].children[0]
        index_of_phi1 = self.list_of_subformula.index(phi1)
        phi2 = hyperproperty.children[0].children[3]
        index_of_phi2 = self.list_of_subformula.index(phi2)

        encoding = []

        # case distinction on the values of k1, k2
        if k2 == 0:
            rel_quant1, rel_quant_stu1, enc1 = self.encodeSemantics(phi1, stutter_scheds)
            relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant1)
            rel_quant2, rel_quant_stu2, enc2 = self.encodeSemantics(phi2, stutter_scheds)

            relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant2)
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)

            relevant_quantifier_stu = copy.deepcopy(relevant_quantifier)
            stutter_scheds0 = self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu)
            stutter_scheds2 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu2)

            encoding = enc1 + enc2

            for r_state in combined_state_list:
                name1 = 'prob'
                for tup in r_state:
                    name1 += "_" + str(tup)
                name1 += "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
                self.addToVariableList(name1)
                name2 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        name2 += "_" + str(r_state[ind])
                    else:
                        name2 += "_" + str((0, 0))
                name2 += "_" + str(index_of_phi2) + "_" + str(stutter_scheds2)
                self.addToVariableList(name2)

                eq1 = Implies(self.dictOfBools[name2],
                              self.dictOfReals[name1] == RealVal(1))
                eq2 = Implies(Not(self.dictOfBools[name2]),
                              self.dictOfReals[name1] == RealVal(0))
                self.no_of_subformula += 2
                encoding.append(And(eq1, eq2))
                self.no_of_subformula += 1

        elif k1 == 0:
            left, k_1, k_2, right = hyperproperty.children[0].children
            hyperproperty_new = Tree('probability', [Tree('until_bounded', [left,
                                                                            k_1,
                                                                            Token('NUM', str(int(k_2.value) - 1)),
                                                                            right])])
            # only needs to be inserted once, not for every stutter_scheds
            if hyperproperty_new not in self.list_of_subformula:
                self.list_of_subformula.append(hyperproperty_new)
            index_of_replaced = self.list_of_subformula.index(hyperproperty_new)
            rel_quant, rel_quant1, rel_quant2, \
                rel_quant_stu, rel_quant_stu1, rel_quant_stu2, \
                encoding = self.encodeBoundedUntilSemantics(hyperproperty_new, stutter_scheds)

            relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant)
            # TODO isnt it unnecessary to add them again since we already added the quantifiers in the base case.
            # OD: Makes sense, but I keopt this for the cases where the bounds are [0,3], then this is the first case it hits.
            # LG: but actually the base case is executed first, since we recursively call BoundedSem
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)

            relevant_quantifier_stu = copy.deepcopy(relevant_quantifier) # = rel_quant_stu due to base case
            stutter_scheds0 = self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu)
            stutter_scheds1 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu1)
            stutter_scheds2 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu2)

            for r_state in combined_state_list:
                # encode cases where we know probability is 0 or 1 and require probs variables to be in [0,1]
                holds1 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant1:
                        holds1 += "_" + str(r_state[ind])
                    else:
                        holds1 += "_" + str((0, 0))
                holds1 += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
                self.addToVariableList(holds1)
                holds2 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) in rel_quant2:
                        holds2 += "_" + str(r_state[ind])
                    else:
                        holds2 += "_" + str((0, 0))
                holds2 += "_" + str(index_of_phi2) + "_" + str(stutter_scheds2)
                self.addToVariableList(holds2)
                prob_phi = 'prob'
                for tup in r_state:
                    prob_phi += "_" + str(tup)
                prob_phi += "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
                self.addToVariableList(prob_phi)

                # new_prob_const_0 = self.dictOfReals[prob_phi] >= float(0)
                # new_prob_const_1 = self.dictOfReals[prob_phi] <= float(1)

                first_implies = And(Implies(self.dictOfBools[holds2],
                                            self.dictOfReals[prob_phi] == RealVal(1)),
                                    Implies(And(Not(self.dictOfBools[holds1]),
                                                Not(self.dictOfBools[holds2])),
                                            self.dictOfReals[prob_phi] == RealVal(0))
                                    )
                self.no_of_subformula += 4
                encoding.append(first_implies)

                # create list of all possible actions for r_state
                dicts_act = []
                for l in range(len(relevant_quantifier)):
                    dicts_act.append(self.model.dict_of_acts[r_state[relevant_quantifier[l] - 1][0]])
                combined_acts = list(itertools.product(*dicts_act))

                # precondition for probability calculation: probability isnt 0 or 1
                implies_precedent = And(self.dictOfBools[holds1],
                                        Not(self.dictOfBools[holds2]))
                self.no_of_subformula += 2

                # encode probability calculation
                sum_of_probs = RealVal(0)
                for ca in combined_acts:
                    # create list of successors of r_state with probabilities under currently considered stuttering and actions
                    combined_succ = self.genSuccessors(r_state, ca, stutter_scheds0, relevant_quantifier)

                    # calculate probability based on probabilities that successor states satisfy the property with bounds decreased by 1
                    for cs in combined_succ:
                        prob_succ = 'prob'
                        product = RealVal(1)

                        for l in range(1, self.no_of_state_quantifier + 1):
                            if l in relevant_quantifier:
                                l_index = relevant_quantifier.index(l)
                                succ_state = cs[l_index][0]
                                prob_succ += "_" + succ_state
                                product *= RealVal(cs[l_index][1])
                                product *= self.dictOfReals["a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                            else:
                                prob_succ += "_" + str((0, 0))

                        prob_succ += "_" + str(index_of_replaced) + "_" + str(stutter_scheds0)
                        self.addToVariableList(prob_succ)
                        product *= self.dictOfReals[prob_succ]

                        sum_of_probs += product
                        self.no_of_subformula += 1

                prob_calc_enc = self.dictOfReals[prob_phi] == sum_of_probs
                self.no_of_subformula += 1
                encoding.append(Implies(implies_precedent, prob_calc_enc))
                self.no_of_subformula += 1

        elif k1 > 0:
            left, k_1, k_2, right = hyperproperty.children[0].children
            hyperproperty_new = Tree('probability', [Tree('until_bounded', [left,
                                                                            Token('NUM', str(int(k_1.value) - 1)),
                                                                            Token('NUM', str(int(k_2.value) - 1)),
                                                                            right])])
            if hyperproperty_new not in self.list_of_subformula:
                self.list_of_subformula.append(
                    hyperproperty_new)  # only needs to be inserted once, not for every stutter_scheds
            index_of_replaced = self.list_of_subformula.index(hyperproperty_new)
            rel_quant, rel_quant1, rel_quant2, \
                rel_quant_stu, rel_quant_stu1, rel_quant_stu2, \
                encoding = self.encodeBoundedUntilSemantics(hyperproperty_new, stutter_scheds) #todo nicer formatting, maybe save as a tuple and unpack later

            relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant)
            combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)

            relevant_quantifier_stu = copy.deepcopy(relevant_quantifier) # = rel_quant due to base case
            stutter_scheds0 = self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu)
            stutter_scheds1 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu1)

            for r_state in combined_state_list:
                # encode cases where we know probability is 0 and require probs variables to be in [0,1]
                holds1 = 'holds'
                for ind in range(0, len(r_state)):
                    if (ind + 1) == rel_quant1:
                        holds1 += "_" + str(r_state[ind])
                    else:
                        holds1 += "_" + str((0, 0))
                holds1 += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
                self.addToVariableList(holds1)
                prob_phi = 'prob'
                for tup in r_state:
                    prob_phi += "_" + str(tup)
                prob_phi += "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
                self.addToVariableList(prob_phi)

                # new_prob_const_0 = self.dictOfReals[prob_phi] >= float(0)
                # new_prob_const_1 = self.dictOfReals[prob_phi] <= float(1)

                first_implies = And(Implies(Not(self.dictOfBools[holds1]),
                                            self.dictOfReals[prob_phi] == RealVal(0))
                                    )
                encoding.append(first_implies)
                self.no_of_subformula += 3

                # create list of all possible actions for r_state
                dicts_act = []
                for l in range(len(relevant_quantifier)):
                    dicts_act.append(self.model.dict_of_acts[r_state[relevant_quantifier[l] - 1][0]])
                combined_acts = list(itertools.product(*dicts_act))

                # precondition for probability calculation: probability isnt 0 or 1
                implies_precedent = self.dictOfBools[holds1]
                self.no_of_subformula += 1

                # encode probability calculation
                sum_of_probs = RealVal(0)
                for ca in combined_acts:
                    # create list of successors of r_state with probabilities under currently considered stuttering and actions
                    combined_succ = self.genSuccessors(r_state, ca, stutter_scheds0, relevant_quantifier)

                    # create equation system for probabilities
                    for cs in combined_succ:
                        prob_succ = 'prob'
                        product = RealVal(1)

                        for l in range(1, self.no_of_state_quantifier + 1):
                            if l in relevant_quantifier:
                                l_index = relevant_quantifier.index(l)
                                succ_state = cs[l_index][0]
                                prob_succ += "_" + succ_state
                                product *= RealVal(cs[l_index][1])
                                product *= self.dictOfReals[
                                    "a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                            else:
                                prob_succ += "_" + str((0, 0))

                        prob_succ += "_" + str(index_of_replaced) + "_" + str(stutter_scheds0)
                        self.addToVariableList(prob_succ)
                        product *= self.dictOfReals[prob_succ]
                        sum_of_probs += product
                        self.no_of_subformula += 1

                prob_calc_enc = self.dictOfReals[prob_phi] == sum_of_probs
                self.no_of_subformula += 1
                encoding.append(Implies(implies_precedent, prob_calc_enc))
                self.no_of_subformula += 1

        return relevant_quantifier, rel_quant1, rel_quant2, relevant_quantifier_stu, rel_quant_stu1, rel_quant_stu2, encoding

    def encodeFutureSemantics(self, hyperproperty, stutter_scheds, prev_relevant_quantifier=[]):
        phi1 = hyperproperty.children[0].children[0]
        index_of_phi1 = self.list_of_subformula.index(phi1)
        index_of_phi = self.list_of_subformula.index(hyperproperty)
        relevant_quantifier, rel_quant_stu1, encoding = self.encodeSemantics(phi1, stutter_scheds, prev_relevant_quantifier)

        # relevant_quantifier = extendWithoutDuplicates(relevant_quantifier, rel_quant1)
        combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)

        relevant_quantifier_stu = copy.deepcopy(relevant_quantifier)
        stutter_scheds1 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu1)
        stutter_scheds0 = self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu)

        for r_state in combined_state_list:
            # encode cases where we know probability is 1 and require probs variables to be in [0,1]
            holds1 = 'holds'
            str_r_state = ""
            for ind in r_state:
                str_r_state += "_" + str(ind)
            holds1 += str_r_state + "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
            self.addToVariableList(holds1)
            prob_phi = 'prob' + str_r_state + "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
            self.addToVariableList(prob_phi)

            #new_prob_const_0 = self.dictOfReals[prob_phi] >= float(0)
            #new_prob_const_1 = self.dictOfReals[prob_phi] <= float(1)

            first_implies = Implies(self.dictOfBools[holds1],
                                        (self.dictOfReals[prob_phi] == RealVal(1)))
            encoding.append(first_implies)
            self.no_of_subformula += 3

            # create list of all possible actions for r_state
            dicts_act = []
            for l in range(len(relevant_quantifier)):
                dicts_act.append(self.model.dict_of_acts[r_state[relevant_quantifier[l] - 1][0]])
            combined_acts = list(itertools.product(*dicts_act))

            # precondition for probability calculation: probability isnt 0 or 1
            implies_precedent = Not(self.dictOfBools[holds1])
            self.no_of_subformula += 1

            # encode probability calculation
            sum_of_probs = RealVal(0)
            loop_condition_list = []

            for ca in combined_acts:
                # create list of successors of r_state with probabilities under currently considered stuttering and actions
                combined_succ = self.genSuccessors(r_state, ca, stutter_scheds0, relevant_quantifier)

                # create equation system for probabilities and a loop condition to ensure correctness
                for cs in combined_succ:
                    prob_succ = 'prob'
                    holds_succ = 'holds'
                    d_current = 'd'
                    d_succ = 'd'
                    product = RealVal(1)
                    sched_prob = RealVal(1)

                    for l in range(1, self.no_of_stutter_quantifier + 1):
                        if l in relevant_quantifier:
                            l_index = relevant_quantifier.index(l)
                            succ_state = cs[l_index][0]
                            prob_succ += "_" + succ_state
                            holds_succ += "_" + succ_state
                            d_succ += "_" + succ_state
                            product *= RealVal(cs[l_index][1])
                            product *= self.dictOfReals["a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                            sched_prob *= self.dictOfReals["a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                        else:
                            prob_succ += "_" + str((0, 0))
                            holds_succ += "_" + str((0, 0))
                            d_succ += "_" + str((0, 0))
                        d_current += "_" + str(r_state[l - 1])

                    prob_succ += "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
                    self.addToVariableList(prob_succ)
                    product *= self.dictOfReals[prob_succ]
                    sum_of_probs += product
                    self.no_of_subformula += 1

                    # loop condition
                    holds_succ += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
                    self.addToVariableList(holds_succ)
                    d_current += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1) # todo stutter_scheds1 or 0 ??
                    self.addToVariableList(d_current)
                    d_succ += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
                    self.addToVariableList(d_succ)
                    loop_condition_list.append(And(sched_prob > RealVal(0),
                                                   Or(self.dictOfBools[holds_succ],
                                                      self.dictOfReals[d_current] > self.dictOfReals[d_succ])
                                                   ))
                    self.no_of_subformula += 3

            prob_calc_enc = self.dictOfReals[prob_phi] == sum_of_probs
            self.no_of_subformula += 1
            if len(loop_condition_list) == 1:
                loop_condition_post = loop_condition_list[0]
            else:
                loop_condition_post = Or(loop_condition_list)
            loop_condition = Implies(self.dictOfReals[prob_phi] > RealVal(0),
                                     loop_condition_post)
            self.no_of_subformula += 2
            implies_antecedent = And(prob_calc_enc, loop_condition)
            self.no_of_subformula += 1
            encoding.append(Implies(implies_precedent, implies_antecedent))
            self.no_of_subformula += 1
        return relevant_quantifier, relevant_quantifier_stu, encoding

    def encodeGlobalSemantics(self, hyperproperty, stutter_scheds, relevant_quantifier=[]):
        index_of_phi = self.list_of_subformula.index(hyperproperty)
        phi1 = hyperproperty.children[0].children[0]
        index_of_phi1 = self.list_of_subformula.index(phi1)
        rel_quant1, rel_quant_stu1, encoding = self.encodeSemantics(phi1, stutter_scheds)

        relevant_quantifier = extendWithoutDuplicates(rel_quant1, relevant_quantifier)
        combined_state_list = self.generateComposedStatesWithStutter(relevant_quantifier)

        relevant_quantifier_stu = copy.deepcopy(relevant_quantifier)
        stutter_scheds0 = self.genRelStutterscheds(stutter_scheds, relevant_quantifier_stu)
        stutter_scheds1 = self.genRelStutterscheds(stutter_scheds, rel_quant_stu1)

        for r_state in combined_state_list:
            # encode cases where we know probability is 0 and require probs variables to be in [0,1]
            holds1 = 'holds'
            str_r_state = ""
            for tup in r_state:
                str_r_state += "_" + str(tup)
            holds1 += str_r_state + "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
            self.addToVariableList(holds1)
            prob_phi = 'prob'
            prob_phi += str_r_state + "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
            self.addToVariableList(prob_phi)

            # new_prob_const_0 = self.dictOfReals[prob_phi] >= float(0)
            # new_prob_const_1 = self.dictOfReals[prob_phi] <= float(1)

            first_implies = Implies((Not(self.dictOfBools[holds1])),
                                    self.dictOfReals[prob_phi] == RealVal(0))
            encoding.append(first_implies)
            self.no_of_subformula += 1

            # create list of all possible actions for r_state
            dicts_act = []
            for l in range(len(relevant_quantifier)):
                dicts_act.append(self.model.dict_of_acts[r_state[relevant_quantifier[l] - 1][0]])
            combined_acts = list(itertools.product(*dicts_act))

            # precondition for probability calculation: probability isnt 0 or 1
            implies_precedent = self.dictOfBools[holds1]
            self.no_of_subformula += 1

            sum_of_probs = RealVal(0)
            loop_condition_list = []

            for ca in combined_acts:
                # create list of successors of r_state with probabilities under currently considered stuttering and actions
                combined_succ = self.genSuccessors(r_state, ca, stutter_scheds0, relevant_quantifier)

                # create equation system for probabilities and a loop condition to ensure correctness
                for cs in combined_succ:
                    prob_succ = 'prob'
                    holds_succ = 'holds'
                    d_current = 'd'
                    d_succ = 'd'
                    product = RealVal(1)
                    sched_prob = RealVal(1)

                    for l in range(1, self.no_of_state_quantifier + 1):
                        if l in relevant_quantifier:
                            l_index = relevant_quantifier.index(l)
                            succ_state = cs[l_index][0]
                            prob_succ += "_" + succ_state
                            holds_succ += "_" + succ_state
                            d_succ += "_" + succ_state
                            product *= RealVal(cs[l_index][1])
                            product *= self.dictOfReals["a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                            sched_prob *= self.dictOfReals["a_" + str(r_state[l - 1][0]) + "_" + str(ca[l_index])]
                        else:
                            prob_succ += "_" + str((0, 0))
                            holds_succ += "_" + str((0, 0))
                            d_succ += "_" + str((0, 0))
                        d_current += "_" + str(r_state[l - 1])

                    prob_succ += "_" + str(index_of_phi) + "_" + str(stutter_scheds0)
                    self.addToVariableList(prob_succ)
                    product *= self.dictOfReals[prob_succ]
                    sum_of_probs += product
                    self.no_of_subformula += 1

                    # loop condition
                    holds_succ += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
                    self.addToVariableList(holds_succ)
                    d_current += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
                    self.addToVariableList(d_current)
                    d_succ += "_" + str(index_of_phi1) + "_" + str(stutter_scheds1)
                    self.addToVariableList(d_succ)
                    loop_condition_list.append(And(sched_prob > RealVal(0),
                                                   Or(Not(self.dictOfBools[holds_succ]),
                                                      self.dictOfReals[d_current] > self.dictOfReals[d_succ])
                                                   ))
                    self.no_of_subformula += 3

            prob_calc_enc = self.dictOfReals[prob_phi] == sum_of_probs
            self.no_of_subformula += 1
            if len(loop_condition_list) == 1:
                loop_condition_post = loop_condition_list[0]
            else:
                loop_condition_post = Or(loop_condition_list)
            loop_condition = Implies(self.dictOfReals[prob_phi] < RealVal(1),
                                     loop_condition_post)
            self.no_of_subformula += 2
            implies_antecedent = And(prob_calc_enc, loop_condition)
            self.no_of_subformula += 1
            encoding.append(Implies(implies_precedent, implies_antecedent))
            self.no_of_subformula += 1

        return relevant_quantifier, relevant_quantifier_stu, encoding
