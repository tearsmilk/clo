plugins {
    java
    id("com.gradleup.shadow") version "9.6.1"
}

group = "ink.hoka"
version = "1.4.1"
description = "Система квестов"

repositories {
    mavenCentral()
    maven("https://repo.papermc.io/repository/maven-public/")
}

dependencies {
    // Paper API 1.21.11 — подходит и для Leaf (это форк Paper).
    compileOnly("io.papermc.paper:paper-api:1.21.11-R0.1-SNAPSHOT")
}

// Тулчейн не пинуем — используется JDK, которым запущен Gradle (JDK 25).
tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    // Байткод под Java 21 — минимум для Paper 1.21.11, запускается и на Java 25.
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
    archiveFileName.set("ZenQuests-${project.version}.jar")
}

tasks.jar { enabled = false }

tasks.build {
    dependsOn(tasks.shadowJar)
}
