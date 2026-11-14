use ratatui::{
    layout::{Alignment, Constraint, Layout, Rect},
    style::{Color, Style, Stylize},
    text::Line,
    widgets::{Block, BorderType, Borders, Paragraph},
    widgets::{List, ListDirection, ListState},
    Frame,
};

use crate::app::App;

/// Glue: split the screen and delegate each area.
pub fn render(app: &mut App, frame: &mut Frame) {
    let outer = Block::default()
        .title("Simple English Sentence Generator")
        .title_alignment(Alignment::Center)
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .style(Style::default().fg(Color::Yellow));
    let inner = outer.inner(frame.area());
    frame.render_widget(outer, frame.area());

    let [options, sentence, help] = Layout::vertical([
        Constraint::Length(6),
        Constraint::Fill(1),
        Constraint::Length(1),
    ])
    .areas(inner);

    render_options(app, frame, options);
    render_sentences(app, frame, sentence);
    render_help(frame, help);
}

fn render_choice_list(frame: &mut Frame, area: Rect, title: &str, items: &[&str], selected: usize) {
    let list = List::new(items.iter().copied())
        .block(Block::bordered().title(title))
        .highlight_symbol("> ")
        .highlight_style(Style::new().reversed());

    let mut state = ListState::default().with_selected(Some(selected));
    frame.render_stateful_widget(list, area, &mut state);
}

fn render_options(app: &App, frame: &mut Frame, area: Rect) {
    let [left, right] = Layout::horizontal([Constraint::Fill(1), Constraint::Fill(1)])
        .areas(area);

    render_choice_list(frame, left, "Time", &["Present", "Past", "Future"], app.time as usize);
    
    render_choice_list(
        frame,
        right,
        "Aspect",
        &["Simple", "Continuous", "Perfect", "Perfect Continuous"],
        app.aspect as usize,
    );
}

fn render_sentences(app: &App, frame: &mut Frame, area: Rect) {
    let lines: Vec<Line> = app.sentences
                            .iter()
                            .map(|s| Line::from(s.as_str()))
                            .collect();
    frame.render_widget(
        Paragraph::new(lines)
            .alignment(Alignment::Center)
            .block(Block::bordered().title("Sentence")),
        area,
    );
}

fn render_help(frame: &mut Frame, area: Rect) {
    frame.render_widget(
        Paragraph::new("t: time · a: aspect · Enter: generate · q/Esc: quit")
            .alignment(Alignment::Center)
            .dim(),
        area,
    );
}