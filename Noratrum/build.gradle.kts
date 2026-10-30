plugins {
    java
    id("com.gradleup.shadow") version "9.6.1"
}

group = "ink.hoka"
version = "o012mk23f87"

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

// Модули живут в прежних папках репо (исходники, gui-specs, betterhud, nexo) — подключаем их исходники и ресурсы.
val modules = mapOf("zenquests" to "../ZenQuests", "zenfishing" to "../ZenFishing", "zengroups" to "../ZenGroups", "zenboosters" to "../ZenBoosters")

sourceSets.main {
    java.srcDirs(modules.values.map { "$it/src/main/java" })
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.release.set(21)
}

tasks.processResources {
    filteringCharset = "UTF-8"
    val props = mapOf("version" to project.version)
    inputs.properties(props)
    filesMatching("paper-plugin.yml") { expand(props) }
    modules.forEach { (ns, dir) -> from("$dir/src/main/resources") { into(ns); exclude("plugin.yml") } }
}

tasks.shadowJar {
    archiveClassifier.set("")
    archiveFileName.set("Noratrum-${project.version}.jar")
}

tasks.jar { enabled = false }
tasks.build { dependsOn(tasks.shadowJar) }
