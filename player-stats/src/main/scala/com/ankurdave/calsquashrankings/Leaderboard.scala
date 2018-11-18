package com.ankurdave.calsquashrankings

import java.io.ByteArrayInputStream
import java.net.URLEncoder
import java.time.LocalDateTime
import java.time.YearMonth
import java.time.ZoneId
import java.time.format.DateTimeFormatter

import com.amazonaws.services.s3.AmazonS3ClientBuilder
import com.amazonaws.services.s3.model.ObjectMetadata
import com.amazonaws.services.s3.model.PutObjectRequest
import com.ankurdave.ttt._
import scalatags.Text
import scalatags.Text.all._

object Leaderboard {
  /** Generates HTML for a leaderboard page containing the given set of players. */
  def apply(
      players: Set[PlayerId], allPlayersStats: AllPlayersStats, filename: String, description: Frag)
    : Leaderboard = {
    val entries =
      (for {
        p <- players
        if allPlayersStats.playerMatchHistory.contains(p)
        numMatches = allPlayersStats.playerMatchHistory(p).size
        curSkill = allPlayersStats.playerRatingHistory(p).last
        lastMonthDate = currentDate.minusMonths(1)
        lastMonthSkill = allPlayersStats.skillVariables.get((lastMonthDate, p))
        lastYearDate = currentDate.minusMonths(12)
        lastYearSkill = allPlayersStats.skillVariables.get((lastYearDate, p))
      } yield (
        p, curSkill, numMatches,
        skillDeltaToString(curSkill, lastMonthSkill),
        skillDeltaToString(curSkill, lastYearSkill)))
        .toSeq.sortBy(_._2.mu).reverse

    new Leaderboard(
      filename,
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
                td(skillDelta12Mo)))))))
  }

  /** Converts a Rating to a string representing its mean. */
  private def skillToString(skill: Rating): String = "%.1f".format(skill.mu)

  /** 
   * Subtracts a skill from a Rating and converts the difference to a string representing the
   * difference in means.
   */
  private def skillDeltaToString(skillA: Rating, skillBOpt: Option[Gaussian]): String =
    skillBOpt match {
      case Some(skillB) if math.abs(skillA.mu - skillB.mu) >= 0.01 =>
        "%+.2f".format(skillA.mu - skillB.mu)
      case _ => ""
    }

  private val currentDate = YearMonth.now()
}

/** Holds a rendered HTML leaderboard for a subset of players. */
class Leaderboard(filename: String, html: String) {
  def uploadToS3(dryRun: Boolean): Unit = {
    val bucket = "ankurdave.com"
    val s3 = AmazonS3ClientBuilder.standard().build()
    val key = s"calsquash-rankings/$filename"
    val htmlBytes = html.getBytes("UTF-8")
    val is = new ByteArrayInputStream(htmlBytes)
    val metadata = new ObjectMetadata
    metadata.setContentType("text/html")
    metadata.setContentLength(htmlBytes.length)
    metadata.setCacheControl("no-cache")
    val req = new PutObjectRequest(bucket, key, is, metadata)
    println("%s -> s3://%s/%s".format(key, bucket, key))
    if (!dryRun) {
      s3.putObject(req)
    }
  }
}
