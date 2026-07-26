package main

import (
	"os"

	"github.com/JiaoZenghao/polytui/implementations/go/internal/cli"
	"github.com/JiaoZenghao/polytui/implementations/go/internal/tui"
)

func main() {
	runner := tui.NewRunner(os.Stdin, os.Stdout)
	os.Exit(cli.Execute(os.Args[1:], os.Stdout, os.Stderr, runner.Run))
}
