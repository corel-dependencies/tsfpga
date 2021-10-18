# --------------------------------------------------------------------------------------------------
# Copyright (c) Lukas Vik. All rights reserved.
#
# This file is part of the tsfpga project.
# https://tsfpga.com
# https://gitlab.com/tsfpga/tsfpga
# --------------------------------------------------------------------------------------------------
# Run the formal.py script in a docker container. Call this script from the root of the tsfpga repo.
# Arguments supplied to this script will be passed to formal.py
# --------------------------------------------------------------------------------------------------

docker run \
  --rm \
  --interactive \
  --tty \
  --user "$(id -u ${USER}):$(id -g ${USER})" \
  --volume $(pwd):/work/repo/tsfpga/tsfpga \
  --volume $(pwd)/../../vunit/vunit:/work/repo/vunit/vunit:ro \
  --workdir /work/repo/tsfpga/tsfpga \
  tsfpga/formal \
  python3 tsfpga/examples/formal.py $@