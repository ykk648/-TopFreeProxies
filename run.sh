# bash run.sh
git pull # --set-upstream my master
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate full
#echo "lite speed test start !"
#./lite-linux-amd64-v3 --config config/lite_config.json --test ./sub/sub_merge_yaml.yaml >speedtest.log 2>&1
#echo "lite speed test done !"
python ./utils/dummy_convert.py
echo "clash yaml gen done !"
git commit -a -m 'update'
git push my HEAD:master