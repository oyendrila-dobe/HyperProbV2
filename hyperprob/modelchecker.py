import copy
import time
import itertools

from lark import Tree
from z3 import Solver, Bool, Real, Int, Or, sat, And, Implies

from hyperprob.utility import common
from hyperprob import propertyparser
from hyperprob.sementicencoder import SemanticsEncoder



class ModelChecker:
    def __init__(self, model, hyperproperty, lengthOfStutter):
        self.model = model
        self.initial_hyperproperty = hyperproperty  # object of property class
        self.solver = Solver()
        self.stutterLength = lengthOfStutter  # default value 1 (no stutter)
        self.list_of_subformula = []
        self.list_of_reals = []
        self.listOfReals = []
        self.list_of_bools = []
        self.listOfBools = []
        self.list_of_ints = []
        self.listOfInts = []
        self.no_of_subformula = 0
        self.no_of_state_quantifier = 0
        self.no_of_stutter_quantifier = 0
        self.state_stutter_mapping = []

    def modelCheck(self):
        non_quantified_property, self.no_of_state_quantifier = propertyparser.findNumberOfStateQuantifier(
            copy.deepcopy(self.initial_hyperproperty.parsed_property))
        non_quantified_property, self.no_of_stutter_quantifier = propertyparser.findNumberOfStutterQuantifier(
            non_quantified_property.children[0])
        non_quantified_property = non_quantified_property.children[0]
        start_time = time.perf_counter()
        self.encodeActions()
        self.encodeStuttering()
        combined_list_of_states = list(
            itertools.product(self.model.getListOfStates(), repeat=self.no_of_state_quantifier))
        combined_list_of_states_with_initial_stutter = list(itertools.product(self.model.getListOfStates(), [0]))
        #extended_states_with_stuttering = list(
            #itertools.product(self.model.getListOfStates(), list(range(self.stutterLength))))
        combined_list_of_states_with_stutter = list(
            itertools.product(combined_list_of_states_with_initial_stutter, repeat=self.no_of_stutter_quantifier))

        if self.initial_hyperproperty.parsed_property.data == 'exist_scheduler':
            self.addToSubformulaList(non_quantified_property)
            self.encodeStateAndStutterQuantifiers(combined_list_of_states_with_stutter)
            common.colourinfo("Encoded quantifiers", False)
            semanticEncoder = SemanticsEncoder(self.model, self.solver,
                                               self.list_of_subformula, self.list_of_bools, self.listOfBools,
                                               self.list_of_ints, self.listOfInts,
                                               self.no_of_subformula, self.no_of_state_quantifier)
            semanticEncoder.encodeSemantics(non_quantified_property)
            common.colourinfo("Encoded non-quantified formula...", False)
            smt_end_time = time.perf_counter() - start_time
            self.printResult(smt_end_time, 'exists')

        elif self.initial_hyperproperty.parsed_property.data == 'forall_scheduler':
            negated_non_quantified_property = propertyparser.negateForallProperty(
                self.initial_hyperproperty.parsed_property)
            self.addToSubformulaList(negated_non_quantified_property)
            self.encodeStateAndStutterQuantifiers(combined_list_of_states_with_stutter)
            common.colourinfo("Encoded quantifiers", False)
            semanticEncoder = SemanticsEncoder(self.model, self.solver,
                                               self.list_of_subformula, self.list_of_bools, self.listOfBools,
                                               self.list_of_ints, self.listOfInts,
                                               self.no_of_subformula, self.no_of_state_quantifier)
            semanticEncoder.encodeSemantics(negated_non_quantified_property)
            common.colourinfo("Encoded non-quantified formula...", False)
            smt_end_time = time.perf_counter() - start_time
            self.printResult(smt_end_time, 'forall')

    def encodeActions(self):
        for state in self.model.parsed_model.states:
            list_of_eqns = []
            name = "a_" + str(state.id)  # a_1 means action for state 1
            self.addToVariableList(name)
            for action in state.actions:
                list_of_eqns.append(self.listOfInts[self.list_of_ints.index(name)] == int(action.id))
            self.solver.add(Or([par for par in list_of_eqns]))
            self.no_of_subformula += 1
        common.colourinfo("Encoded actions in the MDP...")

    def encodeStuttering(self):
        list_over_quantifiers = []
        for loop in range(0, self.no_of_stutter_quantifier):
            list_over_states = []
            for state in self.model.parsed_model.states:
                list_of_equations = []
                for stutter_length in range(0, self.stutterLength):
                    # t_1_3 means stutter duration for state 3 and stutter quantifier 1
                    name = "t_" + str(loop) + "_" + str(state.id)
                    self.addToVariableList(name)
                    list_of_equations.append(self.listOfInts[self.list_of_ints.index(name)] == stutter_length)
                list_over_states.append(Or([par for par in list_of_equations]))
                self.no_of_subformula += 1
            list_over_quantifiers.append(And([par for par in list_over_states]))
        self.solver.add(And([par for par in list_over_quantifiers]))
        common.colourinfo("Encoded stutter actions in the MDP...")

    def addToVariableList(self, name):
        if name[0] == 'h' and not name.startswith('holdsToInt') and name not in self.list_of_bools:
            self.list_of_bools.append(name)
            self.listOfBools.append(Bool(name))
        elif (name[0] in ['p', 'd', 'r'] or name.startswith('holdsToInt')) and name not in self.list_of_reals:
            self.list_of_reals.append(name)
            self.listOfReals.append(Real(name))
        elif name[0] in ['a', 't'] and name not in self.list_of_ints:
            self.list_of_ints.append(name)
            self.listOfInts.append(Int(name))

    def addToSubformulaList(self, formula_phi):  # add as you go any new subformula part as needed
        if formula_phi.data in ['exist_scheduler', 'forall_scheduler', 'exist_state', 'forall_state']:
            formula_phi = formula_phi.children[1]
            self.addToSubformulaList(formula_phi)
        elif formula_phi.data in ['and', 'or', 'implies', 'equivalent',
                                  'less_probability', 'equal_probability', 'greater_probability',
                                  'greater_and_equal_probability', 'less_and_equal_probability',
                                  'less_reward', 'equal_reward', 'greater_reward', 'greater_and_equal_reward',
                                  'less_and_equal_reward',
                                  'add_probability', 'subtract_probability', 'multiply_probability',
                                  'add_reward', 'subtract_reward', 'multiply_reward',
                                  'until_unbounded'
                                  ]:
            if formula_phi not in self.list_of_subformula:
                self.list_of_subformula.append(formula_phi)
            left_child = formula_phi.children[0]
            self.addToSubformulaList(left_child)
            right_child = formula_phi.children[1]
            self.addToSubformulaList(right_child)
        elif formula_phi.data in ['atomic_proposition', 'true', 'constant_probability', 'constant_reward']:
            if formula_phi not in self.list_of_subformula:
                self.list_of_subformula.append(formula_phi)
        elif formula_phi.data in ['next', 'not', 'future', 'global']:
            if formula_phi not in self.list_of_subformula:
                self.list_of_subformula.append(formula_phi)
            self.addToSubformulaList(formula_phi.children[0])
        elif formula_phi.data in ['probability']:
            if formula_phi not in self.list_of_subformula:
                self.list_of_subformula.append(formula_phi)
            self.addToSubformulaList(formula_phi.children[0])
        elif formula_phi.data in ['reward']:
            if formula_phi not in self.list_of_subformula:
                self.list_of_subformula.append(formula_phi)
                prob_formula = Tree('probability', [formula_phi.children[1]])
                self.list_of_subformula.append(prob_formula)
            self.addToSubformulaList(formula_phi.children[1])
        elif formula_phi.data in ['until_bounded']:
            if formula_phi not in self.list_of_subformula:
                self.list_of_subformula.append(formula_phi)
            left_child = formula_phi.children[0]
            self.addToSubformulaList(left_child)
            right_child = formula_phi.children[3]
            self.addToSubformulaList(right_child)

    def encodeStateAndStutterQuantifiers(self, combined_list_of_states_and_stutter):
        list_of_state_AV = []  # will have the OR, AND according to the quantifier in that index in the formula
        list_of_stutter_AV = []  # placeholder to manage stutter quantifier encoding
        # TODO: work to remove assumption of stutter schedulers named in order
        changed_hyperproperty = self.initial_hyperproperty.parsed_property
        while len(changed_hyperproperty.children) > 0:
            if changed_hyperproperty.data in ['exist_scheduler', 'forall_scheduler']:
                changed_hyperproperty = changed_hyperproperty.children[1]
            elif changed_hyperproperty.data == 'exist_state':
                list_of_state_AV.append('V')
                changed_hyperproperty = changed_hyperproperty.children[1]
            elif changed_hyperproperty.data == 'forall_state':
                list_of_state_AV.append('A')
                changed_hyperproperty = changed_hyperproperty.children[1]
            elif changed_hyperproperty.data == 'forall_stutter':
                list_of_stutter_AV.append('AT')
                self.state_stutter_mapping.append(int(changed_hyperproperty.children[1].children[0].value[1:]))
                changed_hyperproperty = changed_hyperproperty.children[2]
            elif changed_hyperproperty.data == 'exist_stutter':
                list_of_stutter_AV.append('VT')
                self.state_stutter_mapping.append(int(changed_hyperproperty.children[1].children[0].value[1:]))
                changed_hyperproperty = changed_hyperproperty.children[2]
            elif changed_hyperproperty.data in ['quantifiedformulastutter', 'quantifiedformulastate']:
                changed_hyperproperty = changed_hyperproperty.children[0]
            else:
                break

        index_of_phi = self.list_of_subformula.index(changed_hyperproperty)

        combined_stutter_range = list(
            itertools.product(list(range(self.stutterLength)), repeat=len(self.model.getListOfStates())))
        # TODO: naming of tau_i_s in algo line 5
        list_of_holds = []
        list_of_precondition = []
        for i in range(len(list_of_stutter_AV)):
            list_of_ands = []
            for sublist in combined_stutter_range:
                list_of_eqs = []
                for state in self.model.getListOfStates():
                    name_tau = "t_" + str(i) + "_" + str(state)
                    self.addToVariableList(name_tau)
                    list_of_eqs.append(self.listOfInts[self.list_of_ints.index(name_tau)] == sublist[state])
                list_of_ands.append(And(list_of_eqs))
            list_of_precondition.append(list_of_ands)

        # TODO: start from the back, compute equation, replace in list, until we are left with the final equation

        for i in range(len(combined_list_of_states_and_stutter)):
            name = "holds_"
            for j in range(self.no_of_state_quantifier):
                name += str(combined_list_of_states_and_stutter[i][j]) + "_"
            name += str(index_of_phi)
            self.addToVariableList(name)
            list_of_holds.append(self.listOfBools[self.list_of_bools.index(name)])


        # Now recursively encode stutter schedulers
        stutter_encoding_i = []
        stutter_encoding_ipo = []
        list_of_state_tuples = itertools.product(self.model.getListOfStates(), repeat=self.no_of_stutter_quantifier)

        # initialize stutter_encoding_ipo
        for state_tuple in list_of_state_tuples:
            if list_of_stutter_AV[self.no_of_stutter_quantifier - 1] == 'AT':
                temp = [Implies(list_of_precondition[self.no_of_stutter_quantifier - 1][i], self.fetch_value(list_of_holds, state_tuple)) for i in range(len(combined_stutter_range))]
            elif list_of_stutter_AV[self.no_of_stutter_quantifier - 1] == 'ET':
                temp = [And(list_of_precondition[self.no_of_stutter_quantifier - 1][i], self.fetch_value(list_of_holds, state_tuple)) for i in range(len(combined_stutter_range))]
        # TODO unfinished!

        ######
        list_of_holds_replace = []
        for i in range(self.no_of_state_quantifier - 1, -1, -1):
            count = -1
            limit = len(list_of_holds)
            quo = 0
            for j in range(limit):
                count += 1
                if count == len(self.model.getListOfStates()) - 1:
                    index = quo * len(self.model.getListOfStates())
                    if list_of_state_AV[i] == 'V':
                        list_of_holds_replace.append(Or([par for par in list_of_holds[index:index + count + 1]]))
                        self.no_of_subformula += 1
                    elif list_of_state_AV[i] == 'A':
                        list_of_holds_replace.append(And([par for par in list_of_holds[index:index + count + 1]]))
                        self.no_of_subformula += 1
                    count = -1
                    quo += 1
            list_of_holds = copy.deepcopy(list_of_holds_replace)
            list_of_holds_replace.clear()
        self.solver.add(list_of_holds[0])
        list_of_holds.clear()
        list_of_holds_replace.clear()

    def checkResult(self):
        starting_time = time.perf_counter()
        truth = self.solver.check()
        z3_time = time.perf_counter() - starting_time
        list_of_actions = None
        if truth == sat:
            z3model = self.solver.model()
            list_of_actions = [None] * len(self.model.getListOfStates())
            for li in z3model:
                if li.name()[0] == 'a':
                    list_of_actions[int(li.name()[2:])] = z3model[li]
        if truth.r == 1:
            return True, list_of_actions, self.solver.statistics(), z3_time
        elif truth.r == -1:
            return False, list_of_actions, self.solver.statistics(), z3_time

    def printResult(self, smt_end_time, scheduler_quantifier):
        common.colourinfo("Checking...", False)
        smt_result, actions, statistics, z3_time = self.checkResult()
        if scheduler_quantifier == 'exists':
            if smt_result:
                common.colouroutput("The property HOLDS!")
                print("\nThe values of variables of the witness are:")
                for i in range(0, len(self.model.getListOfStates())):
                    common.colouroutput("At state " + str(i) + " choose action " + str(actions[i]), False)
            else:
                common.colourerror("The property DOES NOT hold!")
        elif scheduler_quantifier == 'forall':
            if smt_result:
                common.colourerror("The property DOES NOT hold!")
                print("\nThe actions at the corresponding states of a counterexample are:")
                for i in range(0, len(self.model.getListOfStates())):
                    common.colouroutput("At state " + str(i) + " choose action " + str(actions[i]), False)
            else:
                common.colouroutput("The property HOLDS!")
        common.colourinfo("\nTime to encode in seconds: " + str(round(smt_end_time, 2)), False)
        common.colourinfo("Time required by z3 in seconds: " + str(round(z3_time, 2)), False)
        common.colourinfo(
            "Number of variables: " + str(len(self.list_of_ints) + len(self.list_of_reals) + len(self.list_of_bools)),
            False)
        common.colourinfo("Number of formula checked: " + str(self.no_of_subformula), False)
        common.colourinfo("z3 statistics:", False)
        common.colourinfo(str(statistics), False)

    def fetch_value(self, list_with_value, value):
        # assuming value is a tuple
        res = 0
        for i in range(1, len(value)+1):
            res += value[0] * pow(len(self.model.getListOfStates()), i)
        return list_with_value[res]