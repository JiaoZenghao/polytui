package tui

import (
	"errors"
	"os"

	tea "charm.land/bubbletea/v2"
	"golang.org/x/term"
)

var ErrNotTTY = errors.New("interactive mode requires a TTY")

type programSpec struct {
	model   tea.Model
	options []tea.ProgramOption
}

type ProgramRunner func(tea.Model, ...tea.ProgramOption) (tea.Model, error)
type programFactory func(programSpec) (tea.Model, error)

type Runner struct {
	stdin      *os.File
	stdout     *os.File
	isTerminal func(int) bool
	runProgram ProgramRunner
	runSpec    programFactory
}

func NewRunner(stdin, stdout *os.File) Runner {
	return Runner{
		stdin:      stdin,
		stdout:     stdout,
		isTerminal: term.IsTerminal,
		runProgram: func(model tea.Model, options ...tea.ProgramOption) (tea.Model, error) {
			return tea.NewProgram(model, options...).Run()
		},
	}
}

func (runner Runner) Run() error {
	if !runner.isTerminal(int(runner.stdin.Fd())) ||
		!runner.isTerminal(int(runner.stdout.Fd())) {
		return ErrNotTTY
	}
	spec := programSpec{
		model: newModel(),
		options: []tea.ProgramOption{
			tea.WithInput(runner.stdin),
			tea.WithOutput(runner.stdout),
		},
	}
	if runner.runSpec != nil {
		_, err := runner.runSpec(spec)
		return err
	}
	_, err := runner.runProgram(spec.model, spec.options...)
	return err
}
