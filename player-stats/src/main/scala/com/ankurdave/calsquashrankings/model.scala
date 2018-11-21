package com.ankurdave.calsquashrankings

// This file contains case classes that conform to our DynamoDB data model.

/** Schema of the base table (calsquash-matches-cache). */
case class MonthMatches(
  filename: String, matches: Option[Seq[Match]], current_players: Option[Set[String]])

case class Match(winner: String, loser: String, winner_score: Int)
