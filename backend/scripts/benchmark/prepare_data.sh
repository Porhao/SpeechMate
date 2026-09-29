set -e
pip install -q pyarrow "transformers==4.56.2" 2>/dev/null; python -c "import transformers, ctranslate2; print(\"transformers\", transformers.__version__, \"ctranslate2\", ctranslate2.__version__)"
mkdir -p /models/ct2 /models/eval
for repo in mesolitica/malaysian-whisper-small-v3 mesolitica/Malaysian-whisper-large-v3-turbo-v3; do
  out=/models/ct2/$(basename $repo | tr 'A-Z' 'a-z')
  if [ ! -f $out/model.bin ]; then
    echo "converting $repo -> $out"
    ct2-transformers-converter --model $repo --output_dir $out --quantization int8 \
      --copy_files tokenizer.json preprocessor_config.json --low_cpu_mem_usage 2>&1 | tail -4
  fi
  ls -la $out | head
done
[ -f /models/eval/fleurs_ms_test.parquet ] || python -c "
from huggingface_hub import hf_hub_download; import shutil
p = hf_hub_download('google/fleurs', 'ms_my/test/0000.parquet', repo_type='dataset', revision='refs/convert/parquet')
shutil.copy(p, '/models/eval/fleurs_ms_test.parquet')"
ls -la /models/eval
echo PREPARE_DONE
