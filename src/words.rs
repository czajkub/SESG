use color_eyre::Result;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct Noun {
    pub noun: String,
    pub plural: Option<String>,
    pub countability: Countability,
    pub use_an: bool,
    pub freq_rank: u16,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Countability {
    Countable,
    Uncountable,
    PluralOnly,
    Both,
}


#[derive(Debug, Deserialize)]
pub struct Verb {
    pub base: String,
    pub third_singular: String,
    pub past: String,
    pub past_participle: String,
    pub ing: String,
    pub transitivity: Transitivity,
    pub reflexive: bool,
    pub freq_rank: u16,
    pub transitivity_source: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Transitivity {
    Transitive,
    Intransitive,
    Ambitransitive,
}

pub fn read_nouns() -> Result<Vec<Noun>> {
    const NOUNS: &str = include_str!("../data/nouns.csv"); 
    let mut rdr = csv::Reader::from_reader(NOUNS.as_bytes());

    Ok(rdr.deserialize().collect::<Result<_, _>>()?)
}

pub fn read_verbs() -> Result<Vec<Verb>> {
    const VERBS: &str = include_str!("../data/verbs.csv");
    let mut rdr = csv::Reader::from_reader(VERBS.as_bytes());

    Ok(rdr.deserialize().collect::<Result<_, _>>()?)
}
