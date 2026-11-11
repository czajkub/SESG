use color_eyre::Result;
use crate::words::{read_nouns, read_verbs, Noun, Verb};

#[derive(Debug)]
pub struct App {
    pub should_quit: bool,

    nouns: Vec<Noun>,
    verbs: Vec<Verb>,

    time: Time,
    aspect: Aspect,

    // TODO: sentence type
    // affirmative by default

    // TODO: subject options
    // default - "the" + singular noun, skip plural only

    // TODO: object
    // "the" + singular noun if transitive or ambi; none if intransitive

    // So: default sentence without completed todos for now is
    // the <subject> <verb_phrase> the <object>

    pub counter: u8,
}

#[derive(Debug, Default)]
pub enum Time {
    #[default]
    Present,
    Past,
    Future,
}

#[derive(Debug, Default)]
pub enum Aspect {
    #[default]
    Simple,
    Continuous,
    Perfect,
    PerfectContinuous,
}

impl App {
    pub fn new() -> Result<Self> {
        Ok(Self {
            should_quit: false,
            nouns: read_nouns()?,
            verbs: read_verbs()?,
            time: Time::default(),
            aspect: Aspect::default(),
            counter: 0,
        })
    }

    pub fn tick(&self) {}

    pub fn quit(&mut self) {
        self.should_quit = true;
    }

    pub fn increment_counter(&mut self) {
        if let Some(res) = self.counter.checked_add(1) {
            self.counter = res;
        }
    }

    pub fn decrement_counter(&mut self) {
        if let Some(res) = self.counter.checked_sub(1) {
            self.counter = res;
        }
    }

    fn verb_phrase(v: &Verb, time: &Time, aspect: &Aspect) -> String {
        use {Aspect::*, Time::*};
        match (time, aspect) {
            (Present, Simple) => v.third_singular.clone(),
            (Past, Simple) => v.past.clone(),
            (Future, Simple) => format!("will {}", v.base),
            (Present, Continuous) => format!("is {}", v.ing),
            (Past, Continuous) => format!("was {}", v.ing),
            (Future, Continuous) => format!("will be {}", v.ing),
            (Present, Perfect) => format!("has {}", v.past_participle),
            (Past, Perfect) => format!("had {}", v.past_participle),
            (Future, Perfect) => format!("will have {}", v.past_participle),
            (Present, PerfectContinuous) => format!("has been {}", v.ing),
            (Past, PerfectContinuous) => format!("had been {}", v.ing),
            (Future, PerfectContinuous) => format!("will have been {}", v.ing),
        }
    }
}