package cli

import (
	"errors"
	"fmt"
	"io"

	"github.com/JiaoZenghao/polytui/implementations/go/internal/buildinfo"
	"github.com/JiaoZenghao/polytui/implementations/go/internal/tui"
	"github.com/spf13/cobra"
)

func NewRootCommand(runInteractive func() error) *cobra.Command {
	command := &cobra.Command{
		Use:           "polytui",
		Short:         "Learn CLI/TUI development across four languages",
		SilenceErrors: true,
		SilenceUsage:  true,
		Version:       buildinfo.String(),
		RunE: func(*cobra.Command, []string) error {
			return runInteractive()
		},
	}
	command.SetVersionTemplate("{{.Version}}\n")
	return command
}

func Execute(
	args []string,
	stdout io.Writer,
	stderr io.Writer,
	runInteractive func() error,
) int {
	command := NewRootCommand(runInteractive)
	command.SetArgs(args)
	command.SetOut(stdout)
	command.SetErr(stderr)
	if err := command.Execute(); err != nil {
		if errors.Is(err, tui.ErrNotTTY) {
			fmt.Fprintln(stderr, "polytui: interactive mode requires a TTY")
			return 2
		}
		fmt.Fprintln(stderr, "polytui: interactive mode failed")
		return 1
	}
	return 0
}
