package com.ankurdave.calsquashrankings

import org.scalatest.FunSuite

class PlayerStatsGeneratorSuite extends FunSuite {
  test("dry run") {
    new PlayerStatsGenerator(dryRun = true).generateStats()
  }
}
