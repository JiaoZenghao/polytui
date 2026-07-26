use clap::Parser;

use crate::build_info;

#[derive(Debug, Parser)]
#[command(
    name = "polytui",
    about = "Learn CLI/TUI development across four languages",
    version = build_info::VERSION_TEXT
)]
pub struct Cli {}
