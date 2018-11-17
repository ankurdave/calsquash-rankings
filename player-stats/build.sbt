name := "calsquash-rankings"

version := "0.1"

organization := "com.ankurdave"

scalaVersion := "2.12.7"

lazy val root = (project in file(".")).dependsOn(tttProject)

lazy val tttProject = RootProject(uri("git://github.com/ankurdave/ttt-scala.git"))

libraryDependencies += "com.amazonaws" % "aws-lambda-java-core" % "1.1.0"

libraryDependencies += "com.amazonaws" % "aws-lambda-java-events" % "2.2.3"

libraryDependencies += "com.amazonaws" % "aws-java-sdk-dynamodb" % "1.11.452"

libraryDependencies += "com.amazonaws" % "aws-java-sdk-s3" % "1.11.452"

libraryDependencies += "com.gu" %% "scanamo" % "1.0.0-M8"

libraryDependencies += "com.lihaoyi" %% "scalatags" % "0.6.7"

javacOptions ++= Seq("-source", "1.8", "-target", "1.8", "-Xlint")

scalacOptions ++= Seq(
  "-deprecation",
  "-encoding", "UTF-8",
  "-feature",
  "-unchecked",
  "-Xfuture",
  "-Xlint:_",
  "-Ywarn-adapted-args",
  "-Ywarn-dead-code",
  "-Ywarn-inaccessible",
  "-Ywarn-infer-any",
  "-Ywarn-nullary-override",
  "-Ywarn-nullary-unit",
  "-Ywarn-unused-import"
)

scalacOptions in (Compile, console) := Seq.empty

autoAPIMappings := true
