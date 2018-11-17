package com.ankurdave.calsquashrankings

import java.io.ByteArrayInputStream
import java.net.URLEncoder
import java.time.LocalDateTime
import java.time.YearMonth
import java.time.ZoneId
import java.time.format.DateTimeFormatter

import com.amazonaws.services.dynamodbv2.AmazonDynamoDBClientBuilder
import com.amazonaws.services.lambda.runtime.{Context, RequestHandler}
import com.amazonaws.services.s3.AmazonS3ClientBuilder
import com.amazonaws.services.s3.model.ObjectMetadata
import com.amazonaws.services.s3.model.PutObjectRequest
import com.ankurdave.ttt._
import com.gu.scanamo._
import scalatags.Text
import scalatags.Text.all._

case class Rating(date: String, mu: Double, sigma: Double)

case class PlayerMatchResult(date: String, opponent: String, outcome: String, winner_score: Int)

case class PlayerStats(name: String, ratings: Seq[Rating], matches: Seq[PlayerMatchResult])

case class Match(winner: String, loser: String, winner_score: Int)

case class MonthMatches(
  filename: String, matches: Option[Seq[Match]], current_players: Option[Set[String]])

object PlayerStatsGenerator {
  def main(args: Array[String]): Unit = {
    new PlayerStatsGenerator().generateStats()
  }
}

class EmptyType() {}

class PlayerStatsGenerator() extends RequestHandler[EmptyType, String] {
  val dateRegex = """^([a-z]+)(\d{2})\.html$""".r

  def monthToNumber(month: String) = month match {
    case "jan" | "decjan" => 1
    case "feb" => 2
    case "mar" => 3
    case "apr" => 4
    case "may" => 5
    case "jun" | "june" => 6
    case "jul" | "july" => 7
    case "aug" => 8
    case "sep" | "sept" => 9
    case "oct" => 10
    case "nov" => 11
    case "dec" => 12
  }

  val currentDate = Date(YearMonth.now())

  def filenameToDate(f: String): Date = f match {
    case "current.html" => currentDate
    case dateRegex(month, year) => Date(YearMonth.of(2000 + year.toInt, monthToNumber(month)))
  }

  def getMatches(): (Seq[(Date, PlayerId, PlayerId, Int)], Set[PlayerId]) = {
    val dynamo = AmazonDynamoDBClientBuilder.standard().build()
    val matchTable = Table[MonthMatches]("calsquash-matches-cache")
    println("Scanning dynamodb matches")

    val cache: Seq[MonthMatches] = for {
      result <- Scanamo.exec(dynamo)(matchTable.scan())
    } yield result.right.get

    val matches =
      for {
        MonthMatches(filename, monthMatchesOpt, _) <- cache
        date = filenameToDate(filename)
        monthMatches <- monthMatchesOpt.toSeq
        Match(winnerStr, loserStr, winnerScore) <- monthMatches
        winner = PlayerId(winnerStr)
        loser = PlayerId(loserStr)
      } yield (date, winner, loser, winnerScore)

    val currentPlayers =
      (for {
        MonthMatches(filename, _, currentPlayersOpt) <- cache
        if filename == "current.html"
        currentPlayers <- currentPlayersOpt.toSeq
        pName <- currentPlayers
      } yield PlayerId(pName)).toSet

    (matches, currentPlayers)
  }

  def matchesToGames(
    matches: Seq[(Date, PlayerId, PlayerId, Int)]): Seq[(Date, PlayerId, PlayerId)] = {
    (for ((date, winner, loser, winnerScore) <- matches) yield (
      Seq.fill(3) { (date, winner, loser) }
        ++ Seq.fill(6 - winnerScore) { (date, loser, winner) })).flatten
  }

  def generateStats(): Unit = {
    val (matches, currentPlayers) = getMatches()
    val games = matchesToGames(matches)
    val skillHistory = new TTT(new Matches(games)).run()

    val players = (for ((d, w, l, ws) <- matches) yield Seq(w, l)).flatten.toSet

    def str(d: Date): String = d.ym.toString + "-01"

    val playerMatchHistory: Map[PlayerId, Seq[PlayerMatchResult]] =
      (for ((d, w, l, ws) <- matches)
      yield Seq(
        (w, PlayerMatchResult(str(d), l.name, "W", ws)),
        (l, PlayerMatchResult(str(d), w.name, "L", ws))))
        .flatten.groupBy(_._1).mapValues(_.map(_._2).sortBy(_.date))

    val playerRatingHistory: Map[PlayerId, Seq[Rating]] =
      (for (((d, p), r) <- skillHistory.skillVariables.toSeq)
      yield (p, Rating(str(d), r.mu, r.sigma)))
        .groupBy(_._1).mapValues(_.map(_._2).sortBy(_.date))

    println("Generating leaderboards")

    def skillToString(skill: Rating): String = "%.1f".format(skill.mu)

    def skillDeltaToString(skillA: Rating, skillBOpt: Option[Gaussian]): String =
      skillBOpt match {
        case Some(skillB) if math.abs(skillA.mu - skillB.mu) >= 0.01 =>
          "%+.2f".format(skillA.mu - skillB.mu)
        case _ => ""
      }

    def leaderboard(players: Set[PlayerId], filename: String, description: Frag) = {
      val entries =
        (for {
          p <- players
          if playerMatchHistory.contains(p)
          numMatches = playerMatchHistory(p).size
          curSkill = playerRatingHistory(p).last
          lastMonthDate = Date(currentDate.ym.minusMonths(1))
          lastMonthSkill = skillHistory.skillVariables.get((lastMonthDate, p))
          lastYearDate = Date(currentDate.ym.minusMonths(12))
          lastYearSkill = skillHistory.skillVariables.get((lastYearDate, p))
        } yield (
          p, curSkill, numMatches,
          skillDeltaToString(curSkill, lastMonthSkill),
          skillDeltaToString(curSkill, lastYearSkill)))
          .toSeq.sortBy(_._2.mu).reverse

      "<!DOCTYPE html>" + html(
        head(
          meta(attr("http-equiv") := "Content-Type", content := "text/html; charset=utf-8"),
          meta(name := "viewport", content := "width=device-width"),
          link(
            rel := "stylesheet",
            href := "https://ankurdave.com/calsquash-rankings-style.css",
            `type` := "text/css; charset=utf-8"),
          Text.tags2.title(s"$filename - calsquash-rankings")),
        body(
          div(
            id := "container",
            p(
              `class` := "breadcrumb",
              a(
                href := "https://github.com/ankurdave/calsquash-rankings",
                `class` := "project",
                "calsquash-rankings"),
              " / ",
              span(
                `class` := "file",
                filename)),
            p(description),
            p("Generated %s.".format(
              LocalDateTime.now(ZoneId.of("America/Los_Angeles"))
                .format(DateTimeFormatter.ofPattern("yyyy-MM-dd h:mm a")))),
            table(
              tr(
                th("Rank"),
                th("Player"),
                th("Skill"),
                th("# Matches"),
                th("1-mo \u0394 Skill"),
                th("12-mo \u0394 Skill")),
              for (((p, curSkill, numMatches, skillDelta1Mo, skillDelta12Mo), i)
                <- entries.zipWithIndex)
              yield tr(
                td(i + 1),
                td(
                  a(
                    href := "player-stats?name=%s".format(
                      URLEncoder.encode(p.name, "UTF-8")),
                    p.name)),
                td(skillToString(curSkill)),
                td(numMatches),
                td(skillDelta1Mo),
                td(skillDelta12Mo))))))
    }

    val leaderboardAll = leaderboard(players, "rankings-all.html",
      frag(
        "Rankings for all players. See ",
        a(href := "rankings-current.html", "current players"), "."))

    val leaderboardCurrent = leaderboard(currentPlayers, "rankings-current.html",
      span(
        "Rankings for current box league players. See ",
        a(href := "rankings-all.html", "all players"), "."))

    val bucket = "ankurdave.com"
    val s3 = AmazonS3ClientBuilder.standard().build()
    for ((key, content) <- Seq(
      ("calsquash-rankings/rankings-all.html", leaderboardAll.toString),
      ("calsquash-rankings/rankings-current.html", leaderboardCurrent.toString))) {

      val contentBytes = content.getBytes("UTF-8")
      val is = new ByteArrayInputStream(contentBytes)
      val metadata = new ObjectMetadata
      metadata.setContentType("text/html")
      metadata.setContentLength(contentBytes.length)
      metadata.setCacheControl("no-cache")
      val req = new PutObjectRequest(bucket, key, is, metadata)
      println("%s -> s3://%s/%s".format(key, bucket, key))
      s3.putObject(req)
    }

    println("Uploading player stats")

    val dynamo = AmazonDynamoDBClientBuilder.standard().build()
    val playerStatsTable = Table[PlayerStats]("calsquash-player-stats")
    val playerStats: Set[PlayerStats] =
      (for {
        p <- players
        rs = playerRatingHistory(p).sortBy(_.date)
        ms = playerMatchHistory(p).sortBy(_.date)
        s = PlayerStats(p.name, rs, ms)
      } yield s).toSet
    Scanamo.exec(dynamo)(playerStatsTable.putAll(playerStats))
  }

  override def handleRequest(input: EmptyType, context: Context): String = {
    generateStats()
	"Success"
  }
}
