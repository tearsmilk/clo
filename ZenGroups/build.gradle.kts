plugins {
    java
    id("com.gradleup.shadow") version "9.6.1"
}

group = "ink.hoka"
version = "1.0.0"
description = "Группы и права: простая замена LuckPerms"

repositories {
    mavenCentral()
    maven("https://repo.papermc.io/repository/maven-public/")
    maven("https://repo.extendedclip.com/releases/")
    maven("https://jitpack.io")
}

dependencies {
    compileOnly("io.papermc.paper:paper-api:1.21.11-R0.1-SNAPSHOT")
    compileOnly("me.clip:placeholderapi:2.11.6")
    compileOnly("com.github.MilkBowl:VaultAPI:1.7.1")
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.release.set(21)
}

tasks.processResources {
    filteringCharset = "UTF-8"
    val props = mapOf("version" to project.version)
    inputs.properties(props)
    filesMatching("plugin.yml") { expand(props) }
}

tasks.shadowJar {
    archiveClassifier.set("")
    archiveFileName.set("ZenGroups-${project.version}.jar")
}

tasks.jar { enabled = false }
tasks.build { dependsOn(tasks.shadowJar) }
