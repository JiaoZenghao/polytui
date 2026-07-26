package cli

import (
	"github.com/JiaoZenghao/polytui/implementations/go/internal/buildinfo"
	"github.com/spf13/cobra"
)

func NewRootCommand() *cobra.Command {
	command := &cobra.Command{
		Use:           "polytui",
		Short:         "Learn CLI/TUI development across four languages",
		SilenceErrors: true,
		SilenceUsage:  true,
		Version:       buildinfo.String(),
	}
	command.SetVersionTemplate("{{.Version}}\n")
	return command
}
