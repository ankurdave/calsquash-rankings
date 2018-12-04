package com.ankurdave.calsquashrankings

import com.ankurdave.ttt.PlayerId
import scalatags.Text
import scalatags.Text.all._

object PageUtils {
  def playerStatsFilename(p: PlayerId): String =
    p.name.replaceAll("\\W+", "") + ".html"

  def playerStatsLink(p: PlayerId): Frag = {
    a(
      href := "player-stats/" + playerStatsFilename(p),
      p.name)
  }

  def page(
      htmlTitle: Frag,
      pageTitle: Frag,
      headers: Frag,
      content: Frag)
    : String = {

    "<!DOCTYPE html>" + html(
      head(
        meta(attr("charset") := "UTF-8"),
        meta(name := "viewport", attr("content") := "width=device-width"),
        link(
          rel := "stylesheet",
          href := "https://ankurdave.com/calsquash-rankings-style.css",
          `type` := "text/css"),
        Text.tags2.title(htmlTitle, " - calsquash-rankings"),
        headers),
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
            pageTitle),
          content)))
  }
}
