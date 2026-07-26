pub mod app;
pub mod build_info;
pub mod cli;
pub mod tui;

#[cfg(test)]
mod tests {
    use clap::CommandFactory;

    use crate::cli::Cli;

    #[test]
    fn version_flag_uses_shared_version() {
        let command = Cli::command();
        assert_eq!(
            command.render_version().to_string(),
            "polytui 0.1.0-dev.0 (rust)\n"
        );
    }
}
