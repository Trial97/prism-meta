from meta.common.neoforge import NEOFORGE_COMPONENT
from meta.common.forge import FORGEWRAPPER_LIBRARY
from meta.common.mojang import MINECRAFT_COMPONENT
from meta.model import MetaVersion, Dependency, Library, GradleSpecifier
from meta.model.neoforge import NeoForgeInstallerProfileV2
from meta.model.mojang import MojangVersion
import zipfile
import argparse
import os


def split_jar_name(jar_path):
    name = os.path.basename(jar_path).removesuffix(".jar")
    parts = name.split("-", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""


def version_from_build_system_installer(
    installer: MojangVersion,
    profile: NeoForgeInstallerProfileV2,
    rawVersion: str,
    mc_version_sane: str,
    jar_path: str,
) -> MetaVersion:
    v = MetaVersion(name="NeoForge", version=rawVersion, uid=NEOFORGE_COMPONENT)
    v.requires = [Dependency(uid=MINECRAFT_COMPONENT, equals=mc_version_sane)]
    v.main_class = "io.github.zekerzhayard.forgewrapper.installer.Main"

    v.maven_files = []

    jar_name, jar_version = split_jar_name(jar_path)
    installer_lib = Library(
        name=GradleSpecifier("net.neoforged", jar_name, jar_version),
        mmcHint="local",
    )
    v.maven_files.append(installer_lib)

    for forge_lib in profile.libraries:
        if forge_lib.name.is_log4j():
            continue

        v.maven_files.append(forge_lib)

    v.libraries = []

    v.libraries.append(FORGEWRAPPER_LIBRARY)

    for forge_lib in installer.libraries:
        if forge_lib.name.is_log4j():
            continue

        v.libraries.append(forge_lib)

    v.release_time = installer.release_time
    v.order = 5
    mc_args = (
        "--username ${auth_player_name} --version ${version_name} --gameDir ${game_directory} "
        "--assetsDir ${assets_root} --assetIndex ${assets_index_name} --uuid ${auth_uuid} "
        "--accessToken ${auth_access_token} --userType ${user_type} --versionType ${version_type}"
    )
    for arg in installer.arguments.game:
        mc_args += f" {arg}"
    v.minecraft_arguments = mc_args
    return v


#  python -m meta.run.generate_neoforge_from_installer ~/Downloads/neoforge-21.4.114-beta-installer.jar 21.4.144 1.21.4


def main():
    parser = argparse.ArgumentParser(
        description="Extract jar path, version, and MC version."
    )
    parser.add_argument("jar_path", help="Path to the .jar file")
    parser.add_argument("version", help="Version string, e.g. 1.2.3")
    parser.add_argument("mc_version", help="Minecraft version, e.g. 1.20.1")

    args = parser.parse_args()

    with zipfile.ZipFile(args.jar_path) as jar:
        with jar.open("version.json") as profile_zip_entry:
            version_data = profile_zip_entry.read()

            # Process: does it parse?
            installer = MojangVersion.parse_raw(version_data)

        with jar.open("install_profile.json") as profile_zip_entry:
            install_profile_data = profile_zip_entry.read()

            # Process: does it parse?
            profile = NeoForgeInstallerProfileV2.parse_raw(install_profile_data)

    v = version_from_build_system_installer(
        installer, profile, args.version, args.mc_version, args.jar_path
    )

    v.write(f"net.neoforged.json")


if __name__ == "__main__":
    main()
