
import os
import time
import argparse
import importlib.util

import matplotlib.pyplot as graph
from scipy.integrate import ode

from cellsolver.codesamples import hodgkin_huxley_squid_axon_model_1952 as hh


KNOWN_SOLVERS = ['euler', 'dop853', 'vode']


class TimeExecution(object):

    number = 10
    run_timeit = False

    def __init__(self, f):
        self._f = f

    def __call__(self, *args, **kwargs):

        if TimeExecution.run_timeit:
            ts = time.time()
            for _ in range(TimeExecution.number):
                self._f(*args, **kwargs)
            te = time.time()
            print('%r  average = %2.2f ms' %
                  (self._f.__name__, ((te - ts) * 1000)/TimeExecution.number))

        return self._f(*args, **kwargs)


def initialize_system(system):
    rates = system.createRateVector()
    states = system.createStateVector()
    variables = system.createVariableVector()

    system.initializeConstants(states, variables)
    system.computeComputedConstants(variables)

    return states, rates, variables


@TimeExecution
def solve_using_euler(system, step_size, interval):
    states, rates, variables = initialize_system(system)

    results = [[] for _ in range(len(states))]
    x = []

    t = interval[0]
    end = interval[-1]
    while t < end:
        system.computeRates(t, states, rates, variables)
        delta = list(map(lambda var: var * step_size, rates))
        states = [sum(x) for x in zip(states, delta)]

        x.append(t)
        for index, value in enumerate(states):
            results[index].append(value)

        t += step_size

    return x, results


def update(voi, states, system, rates, variables):
    system.computeRates(voi, states, rates, variables)
    return rates


@TimeExecution
def solve_using_dop853(system, step_size, interval):
    return solve_using_scipy(system, "dop853", step_size, interval)


@TimeExecution
def solve_using_vode(system, step_size, interval):
    return solve_using_scipy(system, "vode", step_size, interval)


def solve_using_scipy(system, method, step_size, interval):
    states, rates, variables = initialize_system(system)

    results = [[] for _ in range(len(states))]
    x = []

    solver = ode(update)
    solver.set_integrator(method)
    solver.set_initial_value(states, interval[0])
    solver.set_f_params(system, rates, variables)

    end = interval[-1]
    while solver.successful() and solver.t < end:
        solver.integrate(solver.t + step_size)

        x.append(solver.t)
        for index, value in enumerate(solver.y):
            results[index].append(value)

    return x, results


def module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_valid_file(parser, arg):
    expanded_path = os.path.expanduser(arg)
    expanded_path = os.path.expandvars(expanded_path)
    full_path = os.path.abspath(expanded_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        loaded_module = module_from_file("irrelevant", full_path)
        return loaded_module  # return the actual loaded module
    else:
        parser.error("The file %s does not exist!" % arg)


def process_arguments():
    parser = argparse.ArgumentParser(description="Solve ODE's described by libCellML generated Python output.")
    parser.add_argument('--solver', default=KNOWN_SOLVERS[0],
                        help='specify the solver: {0} (default: {1})'.format(KNOWN_SOLVERS, KNOWN_SOLVERS[0]))
    parser.add_argument('--timeit', action='store', type=int, nargs='?', const=10, default=0,
                        help='number of iterations for evaluating execution elapsed time (default: 0)')
    parser.add_argument('--interval', action='store', type=float, nargs=2, default=[0.0, 100.0],
                        help='interval to run the simulation for (default: [0.0, 100.0])')
    parser.add_argument('--step-size', action='store', type=float, nargs=1, default=0.001,
                        help='the step size to output results at (default: 0.001)')
    parser.add_argument('module', nargs='?', default=hh, type=lambda file_name: is_valid_file(parser, file_name),
                        help='a module of Python code generated by libCellML')

    return parser


def plot_solution(x, y_n):
    graph.xlabel("Time (msecs)")
    graph.ylabel("Y-axis")
    graph.title("A test graph")
    for index, result in enumerate(y_n):
        graph.plot(x, result, label='state {0}'.format(index))
    graph.legend()
    graph.show()


def main():

    parser = process_arguments()
    args = parser.parse_args()

    TimeExecution.run_timeit = args.timeit > 0
    if TimeExecution.run_timeit:
        TimeExecution.number = args.timeit

    valid_solution = True
    if args.solver == "euler":
        [x, y_n] = solve_using_euler(args.module, args.step_size, args.interval)
    elif args.solver == "dop853":
        [x, y_n] = solve_using_dop853(args.module, args.step_size, args.interval)
    elif args.solver == "vode":
        [x, y_n] = solve_using_vode(args.module, args.step_size, args.interval)
    else:
        x = []
        y_n = []
        valid_solution = False
        print("Unknown solver '{0}'.".format(args.solver))
        parser.print_help()

    if valid_solution:
        plot_solution(x, y_n)


if __name__ == "__main__":
    main()
