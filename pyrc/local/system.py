import os
import shutil

def _create_directory(dir_path):
    os.mkdir(dir_path)

def remove_directory(dir_path):
	for the_file in os.listdir(dir_path):
		file_path = os.path.join(dir_path, the_file)
		try:
			if os.path.isfile(file_path):
				os.unlink(file_path)
			if os.path.isdir(file_path):
				remove_directory(file_path)
		except Exception as e:
			raise(e)

	os.rmdir(dir_path)

def remove_file(file_path):
	os.unlink(file_path)


def cpfile(src_file, dest):
	dest_file = None

	if not os.path.isfile(src_file):
		raise RuntimeError("Cannot copy, source is not a file.")

	if os.path.isfile(dest):
		dest_file = dest
		
	if os.path.isdir(dest):
		src_file_name = os.path.split(src_file)[1]
		dest_file = os.path.join(dest, src_file_name)
	
	shutil.copyfile(src_file, dest_file)

def create_directory(dir_path, override = False):
    # Check if directory already exists :
	if os.path.isfile(dir_path):
		raise RuntimeError("Given file is a file and not a directory.")

	if os.path.isdir(dir_path):
		if override:
			remove_directory(dir_path)
		else:
			raise RuntimeError("Directory " + dir_path + " already exists.")
	
	_create_directory(dir_path)

def list_all_recursivly(folder, ext = None, files_to_exclude = []):
	files = {}
	check_for_ext = False
	ext = [] if ext is None else ext
	ext = [ext] if len(ext) == 1 else ext

	for root, directories, filenames in os.walk(folder):
		if root not in files_to_exclude:
			for filename in filenames:
				if len(ext) > 0:
					for e in ext:
						if filename.endswith(e):
							if root not in files:
								files[root] = []
							if filename not in files_to_exclude:
								files[root].append(filename)
				else:
					if root not in files:
						files[root] = []
					if filename not in files_to_exclude:
						files[root].append(filename)

	return files

def get_size(start_path = '.'):
	total_size = 0
	for dirpath, dirnames, filenames in os.walk(start_path):
		for f in filenames:
			fp = os.path.join(dirpath, f)
			# skip if it is symbolic link
			if not os.path.islink(fp):
				total_size += os.path.getsize(fp)
				
	return total_size