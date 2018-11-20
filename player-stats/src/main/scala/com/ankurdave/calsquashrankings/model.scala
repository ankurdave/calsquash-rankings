package com.ankurdave.calsquashrankings

// This file contains case classes that conform to our DynamoDB data model.

case class Rating(date: String, mu: Double, sigma: Double)

case class PlayerMatchResult(
  date: String, opponent: String, outcome: String, winner_score: Int,
  opponent_mu: Double)

case class PlayerStats(name: String, ratings: Seq[Rating], matches: Seq[PlayerMatchResult])

case class Match(winner: String, loser: String, winner_score: Int)

case class MonthMatches(
  filename: String, matches: Option[Seq[Match]], current_players: Option[Set[String]])
