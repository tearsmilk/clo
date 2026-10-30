plugins {
    java
    id("com.gradleup.shadow") version "9.6.1"
}

group = "ink.hoka"
version = "1.0.2"
description = "Quastres: полублоки на состояниях костра (Nexo-предметы, своя модель на каждое состояние)"

repositories {
    mavenCentral()
    maven("https://repo.papermc.io/repository/maven-public/")
}

dependencies {
    compileOnly("io.papermc.paper:paper-api:1.21.11-R0.1-SNAPSHOT")
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
}

tasks.shadowJar {
    archiveClassifier.set("")
    archiveFileName.set("Quastres-${project.version}.jar")
}

tasks.jar { enabled = false }
tasks.build { dependsOn(tasks.shadowJar) }
