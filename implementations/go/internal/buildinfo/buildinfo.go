package buildinfo

import "fmt"

const (
	Version  = "0.1.0-dev.0"
	Language = "go"
)

func String() string {
	return fmt.Sprintf("polytui %s (%s)", Version, Language)
}
