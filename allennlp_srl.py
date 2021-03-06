"""
Usage:
    python allennlp_srl.py \
    https://s3-us-west-2.amazonaws.com/allennlp/models/srl-model-2017.09.05.tar.gz \
    examples.json
Note:
    each line in examples.json is one sentence, such as:
        Which NFL team represented the AFC at Super Bowl 50?
        Where did Super Bowl 50 take place?
        Which NFL team won Super Bowl 50?
        What color was used to emphasize the 50th anniversary of the Super Bowl?
        What was the theme of Super Bowl 50?
        What day was the game played on?
        What is the AFC short for?
        What was the theme of Super Bowl 50?
        What does AFC stand for?
        What day was the Super Bowl played on?
        Who won Super Bowl 50?
        What venue did Super Bowl 50 take place in?
"""



from allennlp.service.predictors import Predictor
from allennlp.models.archival import load_archive
from contextlib import ExitStack
import argparse
import json

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive_file', type=str, help='the archived model to make predictions with')
    parser.add_argument('input_file', type=argparse.FileType('r'), help='path to input file')

    parser.add_argument('--output-file', type=argparse.FileType('w'), help='path to output file')

    parser.add_argument('--batch-size', type=int, default=1, help='The batch size to use for processing')

    parser.add_argument('--cuda-device', type=int, default=-1, help='id of GPU to use (if any)')

    args = parser.parse_args()

    return args

def get_predictor(args):
    archive = load_archive(args.archive_file,
                           weights_file=None,
                           cuda_device=args.cuda_device,
                           overrides="")

    # Otherwise, use the mapping
    model_type = archive.config.get("model").get("type")
    if model_type != 'srl':
        raise Exception('the given model is not for srl.')
    return Predictor.from_archive(archive, 'semantic-role-labeling')


def run(predictor,
        input_file,
        output_file,
        batch_size,
        print_to_console,
        cuda_device):

    def _run_predictor(batch_data):
        if len(batch_data) == 1:
            result = predictor.predict_json(batch_data[0], cuda_device)
            # Batch results return a list of json objects, so in
            # order to iterate over the result below we wrap this in a list.
            results = [result]
        else:
            results = predictor.predict_batch_json(batch_data, cuda_device)

        for model_input, output in zip(batch_data, results):
            string_output = predictor.dump_line(output)
            if print_to_console:
                print("input: ", model_input)
                print("prediction: ", string_output)
            if output_file:
                output_file.write(string_output)


    batch_data = []
    for line in input_file:
        if not line.isspace():
            line = {"sentence":line.strip()}
            line = json.dumps(line)
            json_data = predictor.load_line(line)
            batch_data.append(json_data)
            if len(batch_data) == batch_size:
                _run_predictor(batch_data)
                batch_data = []

    if batch_data:
        _run_predictor(batch_data)


def main():
    args = get_arguments()
    predictor = get_predictor(args)
    output_file = None
    print_to_console = False
    # ExitStack allows us to conditionally context-manage `output_file`, which may or may not exist
    with ExitStack() as stack:
        input_file = stack.enter_context(args.input_file)  # type: ignore
        if args.output_file:
            output_file = stack.enter_context(args.output_file)  # type: ignore

        if not args.output_file:
            print_to_console = True
        input_file = "https://s3-us-west-2.amazonaws.com/allennlp/models/srl-model-2017.09.05.tar.gz"

        run(predictor,
            input_file,
            output_file,
            args.batch_size,
            print_to_console,
            args.cuda_device)

if __name__ == '__main__':
    main()